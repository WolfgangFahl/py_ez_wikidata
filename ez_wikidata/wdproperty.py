"""
Created on 02.03.2024-03-02

@author: wf
"""
from sqlmodel import Field, SQLModel
from sqlalchemy import event
import os
from dataclasses import dataclass,field
from enum import Enum, auto
from lodstorage.sparql import SPARQL
from lodstorage.yamlable import lod_storable
from lodstorage.sql_cache import Cached, SqlDB
from typing import Any, Dict, List,Union, Optional
import re
from ez_wikidata.prefixes import Prefixes
from pathlib import Path
from lodstorage.query import Query,QueryManager

class WdDatatype(Enum):
    """
    Supported Wikidata datatypes, sorted by frequency and including special cases.
    """
    extid = auto()  # ExternalId: 8645 occurrences
    itemid = auto()  # WikibaseItem: 1634 occurrences
    quantity = auto()  # Quantity: 652 occurrences
    string = auto()  # String: 329 occurrences
    url = auto()  # Url: 107 occurrences
    commons_media = auto()  # CommonsMedia: 79 occurrences
    time = auto()  # Time: 66 occurrences
    text = auto()  # Monolingualtext: 62 occurrences
    math = auto()  # Math: 36 occurrences
    wikibase_property = auto()  # WikibaseProperty: 21 occurrences
    wikibase_sense = auto()  # WikibaseSense: 19 occurrences
    wikibase_lexeme = auto()  # WikibaseLexeme: 17 occurrences
    globe_coordinate = auto()  # GlobeCoordinate: 11 occurrences
    wikibase_form = auto()  # WikibaseForm: 9 occurrences
    musical_notation = auto()  # MusicalNotation: 6 occurrences
    tabular_data = auto()  # TabularData: 6 occurrences
    geoshape = auto()  # GeoShape: 3 occurrences
    # Special cases:
    item = auto()  # Item: Special case
    year = auto()  # Year: Special case
    date = auto()  # Date: Special case
    
    @classmethod
    def from_wb_type_name(cls,wb_type_name:str)->'WdDatatype':
        """
        convert a wikibase type name to a WdDatatype
        
        Args:
            wb_type_name(str): the string name of the wikibase type (with or without wikibase ontology prefix) 
        """
        type_map={
            "ExternalId": cls.extid, 
            "WikibaseItem": cls.itemid,
            "Quantity": cls.quantity,
            "String": cls.string,
            "Url": cls.url,
            "CommonsMedia": cls.commons_media,
            "Time": cls.time,
            "Monolingualtext": cls.text,
            "Math": cls.math,
            "WikibaseProperty": cls.wikibase_property,
            "WikibaseSense": cls.wikibase_sense,
            "WikibaseLexeme": cls.wikibase_lexeme,
            "GlobeCoordinate": cls.globe_coordinate,
            "WikibaseForm": cls.wikibase_form,
            "MusicalNotation": cls.musical_notation,
            "TabularData": cls.tabular_data,
            "GeoShape": cls.geoshape
        }
        wb_type_name=wb_type_name.replace("http://wikiba.se/ontology#","")
        wd_type=type_map.get(wb_type_name,WdDatatype.string)
        return wd_type
        

    @classmethod
    def _missing_(cls, _value):
        """
        default datatype
        """
        return cls.text

    @classmethod
    def get_by_wikibase(cls, property_type: str) -> Union["WdDatatype", None]:
        """
        Get WdDatatype by the corresponding wikibase datatype
        Args:
            property_type: wikibase name of the type

        Returns:
            WdDatatype
        """
        wikibase_map = {
            "WikibaseItem": cls.itemid,
            "Time": cls.date,
            "Monolingualtext": cls.text,
            "String": cls.string,
            "ExternalId": cls.extid,
            "Url": cls.url,
        }
        return wikibase_map.get(property_type, None)
    
class Variable:
    """
    Variable e.g. name handling
    """

    @classmethod
    def validVarName(cls, varStr: str) -> str:
        """
        convert the given potential variable name string to a valid
        variable name

        see https://stackoverflow.com/a/3305731/1497139

        Args:
            varStr(str): the string to convert

        Returns:
            str: a valid variable name
        """
        return re.sub("\W|^(?=\d)", "_", varStr)


class WikidataProperty(SQLModel, table=True):
    """
    Represents a Wikidata Property.
    """
    __table_args__ = {'extend_existing': True}
    
    pid: str = Field(primary_key=True)  # The property ID 
    lang: str = Field(primary_key=True)
    plabel: str # the label of the property
    description: str  # Description of the property
    type_name: str # the type name
    reverse: bool = False  # Indicates if the property is used in reverse direction
    # Variables initialized in __post_init__
    #varname: str = field(init=False)
    #valueVarname: str = field(init=False)
    #labelVarname: str = field(init=False)
    #ptype: WdDatatype = field(init=False) 

    @staticmethod
    def after_load(self, _context):
        """
        Function to run after an instance of WikidataProperty 
        is loaded from the database to
        create and modify calculated fields
        """
        self.pid=self.pid.replace("http://www.wikidata.org/entity/","")
        self.url=f"https://www.wikidata.org/wiki/Property:{self.pid}"
        self.ptype=WdDatatype.from_wb_type_name(self.type_name)
        self.varname = Variable.validVarName(self.plabel)
        self.valueVarname = f"{self.varname}Item" if "WikibaseItem" in self.type_name else self.varname
        self.labelVarname = self.varname
    
    def getPredicate(self):
        """
        get me as a Predicate
        """
        reverseToken = "^" if self.reverse else ""
        plabel = f"{reverseToken}wdt:{self.pid}"
        return plabel

    def __str__(self):
        text = self.pid
        if hasattr(self, "plabel"):
            text = f"{self.plabel} ({self.pid})"
        return text

    
class WikidataPropertyManager:
    """
    handle Wikidata Properties
    """  
    def __init__(self,
        endpoint_url:str="https://qlever.cs.uni-freiburg.de/api/wikidata",
        langs:List[str]=["en","de","fr"],
        debug:bool=False):
        """
        initialize the lookups
        """
        if not "en" in langs:
            raise ValueError(f"en is mandatory in langs -{langs}")
        self.debug=debug
        self.qm=QueryManager(lang='sparql',debug=self.debug)
        self.sparql=SPARQL(endpoint_url,debug=self.debug)
        sql_db_path=WikidataPropertyManager.get_cache_path()
        self.sql_db=SqlDB(sql_db_path)
        query_name=f"wikidata_properties"
        sparql_query=self.get_query_for_langs(langs)
        query=Query(name=query_name,query=sparql_query)
        self.qm.queriesByName[query_name]=query
        cached_props=Cached(WikidataProperty,self.sparql,self.sql_db,query_name,debug=self.debug)
        event.listens_for(WikidataProperty, "load", WikidataProperty.after_load)
        prop_records=cached_props.fetch_or_query(self.qm)
        if not prop_records:
            raise Exception(f"Could not fetch wikidata properties for {langs}")
        props=cached_props.to_entities()
        self.props_by_lang={}
        for lang in langs:
            self.props_by_lang[lang]={}
        self.props_by_id={}
        for prop in props:
            self.props_by_lang[prop.lang][prop.plabel]=prop
            if prop.lang=="en":
                self.props_by_id[prop.pid]=prop
            
    def get_mappings_for_records(
        self, prop_mapping_records: Dict[str, dict]
    ) -> List["PropertyMapping"]:
        """
        convert given list of property mapping records to list of PropertyMappings
        Args:
            prop_mapping_records: records to convert

        Returns:
            property mappings
        """
        mappings = []
        for record in prop_mapping_records.values():
            mapping = PropertyMapping.from_record(self,record)
            mappings.append(mapping)
        return mappings
    

    def get_query_for_langs(self, langs: list=["en","de","fr"]) -> str:
        """
        Get the SPARQL query for the given list of langs.
        """
        query_prefix = Prefixes.getPrefixes(["wikibase", "rdfs", "schema"])
        query_body = ""

        for lang in langs:
            if query_body:  # If not the first iteration, add UNION
                query_body += "UNION\n"
            query_body += f"""
            {{
              ?property a wikibase:Property;
              rdfs:label ?propertyLabel;
              schema:description ?propertyDescription;
              wikibase:propertyType ?wbType.
              FILTER(LANG(?propertyLabel) = "{lang}") .
              FILTER(LANG(?propertyDescription) = "{lang}") .
              BIND("{lang}" AS ?lang)
            }}
            """

        query = query_prefix + "SELECT \n" \
                "  (STR(?property) AS ?pid)\n" \
                "  ?lang\n" \
                "  (?propertyLabel AS ?plabel)\n" \
                "  (?propertyDescription AS ?description)\n" \
                "  (STR(?wbType) AS ?type_name)\n" \
                "WHERE {\n" + query_body + "}\n"
        return query
    
    @classmethod
    def get_instance(cls,
        endpoint_url:str="https://qlever.cs.uni-freiburg.de/api/wikidata",
    )->"WikidataPropertyManager":
        """
        initialize the wikidata property manager
        
        Args:
            endpoint_url(str): the SPARQL endpoint to query if there is no cache available
            lang(str): the languages to query propery labels and descriptions for
        """
        if not hasattr(cls,"wpm"):
            cls.wpm=WikidataPropertyManager(endpoint_url)
        return cls.wpm
    
    @classmethod
    def get_cache_path(cls,lang:str="en")->str:
        home = str(Path.home())
        cache_dir = f"{home}/.wikidata"
        os.makedirs(cache_dir,exist_ok=True)
        cache_path= f"{cache_dir}/wikidata_properties.db"
        return cache_path
    
    def get_properties_by_labels(self, labels: List[str], lang:str="en") -> Dict[str, WikidataProperty]:
        """
        Get properties by their labels for a specific language.
        
        Args:
            labels: List of property labels to search for.
            lang: the language to match with
        Returns:
            A dictionary of {label: WikidataProperty} for found properties.
        """
        matched_properties = {}
        # Check if language exists in cached properties
        # Iterate over requested labels and try to find them in the cached properties
        for label in labels:   
            if label in self.props_by_lang[lang]:
                matched_properties[label] = self.props_by_lang[lang][label]
        return matched_properties
    
    def get_properties_by_ids(self, ids: List[str]) -> Dict[str, Optional[WikidataProperty]]:
        """
        Get properties by their IDs for a specific language.

        Args:
            ids: List of property IDs to search for.

        Returns:
            A dictionary of {property ID: WikidataProperty or None} for found and not found properties.
        """
        matched_properties = {}
        for pid in ids:
            if pid in self.props_by_id:
                matched_properties[pid] = self.props_by_id[pid]
            elif pid in self.wpm_en.props_by_id:
                matched_properties[pid] = self.wpm_en.props_by_id[pid]
        return matched_properties
    
    def get_property_by_id(self, property_id: str) -> WikidataProperty:
        """
        lookup a WikidataProperty for the given property_id

        Args:
            property_id(str): a property ID e.g. "P6375"
        """
        properties = self.get_properties_by_ids([property_id])
        prop_count = len(properties)
        if prop_count == 1:
            return list(properties.values())[0]
        elif prop_count == 0:
            return None
        else:
            property_labels = list(properties.keys())
            msg = f"unexpected get_property_by_id result for property id {property_id}. Expected 0 or 1 results bot got:{property_labels}"
            raise ValueError(msg)
        pass

@lod_storable
class PropertyMapping:
    """
    Represents a single column Wikidata property mapping.

    Attributes:
        column (Optional[str]): The column name in the data source; if None, the value is directly used.
        propertyName (str): The human-readable name of the property.
        propertyId (str): The Wikidata property ID (e.g., "P31").
        propertyType (str): The type of the property as a string; converted to an enum in post-init.
        qualifierOf (Optional[str]): Specifies if the property is a qualifier of another property.
        valueLookupType (Optional[Any]): The type (instance of/P31) of the property value for lookup if the value is not already a QID.
        value (Optional[Any]): The default value to set for the property.
        varname (Optional[str]): An optional variable name for internal use.
        property_type_enum (WdDatatype): The enum representation of the property type, initialized based on propertyType.
   
    The __post_init__ method ensures the propertyType is correctly interpreted and stored as both a string and an enum.
    """
    column: Union[str,None]  # if None, the value is used
    propertyName: str
    propertyId: str
    propertyType: str    
    qualifierOf: str = None
    valueLookupType: Any = None  # type (instance of/P31) of the property value → used to lookup the qid if property value if value is not already a qid
    value: Any = None  # set this value for the property
    varname: str = None
    #property_type_enum: WdDatatype=field(init=False)
    
    def __post_init__(self):
        """
        Convert propertyType from string to WdDatatype enum if necessary
        """
        self.property_type_enum=None
        if isinstance(self.propertyType, str):
            try:
                self.property_type_enum = WdDatatype[self.propertyType]
            except KeyError:
                raise ValueError(f"Invalid property type: {self.propertyType}")
        else:
            self.property_type_enum = self.propertyType
            # Ensure propertyType is stored as the correct string representation of the enum for YAML compatibility
            self.propertyType = self.property_type_enum.name

    @classmethod
    def get_legacy_mapping(cls) -> dict:
        """
        Returns the Mapping from old prop map keys to the new once
        """
        return {
            "Column": "column",
            "PropertyName": "propertyName",
            "PropertyId": "propertyId",
            "Type": "propertyType",
            "Qualifier": "qualifierOf",
            "Lookup": "valueLookupType",
            "Value": "value",
            "PropVarname": "varname",
        }

    @classmethod
    def from_record(cls, wpm:WikidataPropertyManager, record: dict) -> "PropertyMapping":
        """
        initialize PropertyMapping from the given record
        Args:
            wpm(WikidataPropertyManager): to be used for type lookup
            record(Dict): property mapping information

        Returns:
            PropertyMapping
        """
        legacy_lookup = cls.get_legacy_mapping()
        record = record.copy()
        for i in range(len(record)):
            key = list(record.keys())[i]
            if key in legacy_lookup:
                record[legacy_lookup[key]] = record[key]
        # handle missing property type
        property_type = record.get("propertyType", None)
        if property_type in [None, ""]:
            if record.get("valueLookupType", None) not in [None, ""]:
                property_type = WdDatatype.itemid
            elif record.get("value", None) not in [None, ""]:
                property_type = WdDatatype.itemid
        if property_type is not None and not isinstance(property_type, WdDatatype):
            if property_type in [wd.name for wd in WdDatatype]:
                property_type = WdDatatype[property_type]
            else:
                pid=record.get("propertyId")
                props=wpm.get_properties_by_ids([pid])
                if len(props)==1:
                    prop=list(props.values())[0]
                    property_type=prop.ptype
        mapping = PropertyMapping(
            column=record.get("column", None),
            propertyName=record.get("propertyName", None),
            propertyId=record.get("propertyId", None),
            propertyType=property_type,
            qualifierOf=record.get("qualifierOf", None),
            valueLookupType=record.get("valueLookupType", None),
            value=record.get("value", None),
            varname=record.get("varname", None),
        )
        return mapping

    def to_record(self) -> dict:
        """
        convert property mapping to its dict representation
        """
        key_map = self.get_legacy_mapping()
        record = dict()
        for old_key, new_key in key_map.items():
            record[old_key] = getattr(self, new_key, None)
        return record

    def is_qualifier(self) -> bool:
        """
        Returns true if the property mapping describes a qualifier
        """
        is_qualifier = not (self.qualifierOf is None or self.qualifierOf == "")
        return is_qualifier

    @classmethod
    def getDefaultItemPropertyMapping(cls) -> "PropertyMapping":
        """
        get the defaultItemPropertyMapping
        """
        if not hasattr(cls, "defaultItemPropertyMapping"):
            item_prop_map = PropertyMapping(
                column="item",
                propertyName="item",
                propertyId="",
                propertyType=WdDatatype.item,
                varname="item",
            )
            cls.defaultItemPropertyMapping = item_prop_map
        return cls.defaultItemPropertyMapping

    def is_item_itself(self) -> bool:
        """
        Check if the property_type is an item
        
        Returns:
            bool: True if the property mapping links to the existing item 
        """
        is_item_id= self.property_type_enum == WdDatatype.item
        return is_item_id
    
    @classmethod
    def get_qualifier_lookup(
        cls, properties: List["PropertyMapping"]
    ) -> Dict[str, List["PropertyMapping"]]:
        """
        Get a lookup for a property and all its qualifier
        
        Args:
            properties: property mappings to generate the lookup from
        
        Returns:
             dict as property qualifier lookup
        """
        res = dict()
        for pm in properties:
            if not isinstance(pm, PropertyMapping):
                continue
            if pm.qualifierOf is None or pm.qualifierOf == "":
                continue
            else:
                if pm.qualifierOf in res:
                    res[pm.qualifierOf].append(pm)
                else:
                    res[pm.qualifierOf] = [pm]
        return res

    @classmethod
    def get_item_mapping(
        cls, property_mappings: List["PropertyMapping"]
    ) -> "PropertyMapping":
        """
        get the property mapping that is used for the default "item" primary key
        if no property is defined use the default "item" mapping
        """
        for pm in property_mappings:
            if pm.is_item_itself():
                return pm
        pm = cls.getDefaultItemPropertyMapping()
        return pm
    
@lod_storable
@dataclass
class PropertyMappings:
    """
    A collection of Wikidata property mappings, with metadata.
    """
    name: str
    mappings: Dict[str, PropertyMapping] = field(default_factory=dict)
    description: Optional[str] = None
    url: Optional[str] = None