"""
Created on 02.03.2024-03-02

@author: wf
"""
import os
from dataclasses import dataclass,field, InitVar
from enum import Enum, auto
from lodstorage.sparql import SPARQL
from lodstorage.yamlable import lod_storable
from typing import Any, Dict, List,Union, Optional
import re
from ez_wikidata.prefixes import Prefixes
from pathlib import Path

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

@lod_storable
class WikidataProperty:
    """
    Represents a Wikidata Property.
    """
    pid: str  # The property ID
    plabel: str # the label of the property
    description: str  # Description of the property
    type_name: str # the type name
    lang: str="en" # the language 
    reverse: bool = False  # Indicates if the property is used in reverse direction
    # Variables initialized in __post_init__
    varname: str = field(init=False)
    valueVarname: str = field(init=False)
    labelVarname: str = field(init=False)
    ptype: WdDatatype = field(init=False) 
    
    def __post_init__(self):
        """
        create calculated fields
        """
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
    
@lod_storable
class WikidataPropertyManager:
    """
    handle Wikidata Properties
    """
    props: Dict[str, Dict[str, WikidataProperty]] = field(default_factory=dict)
  
    def __post_init__(self):
        """
        initialize the lookups
        """
        self.props_by_id={}
        for lang, properties in self.props.items():
            self.props_by_id[lang] = {prop.pid: prop for prop in properties.values()}

      
    def fetch_props_for_lang(self,endpoint_url:str="https://query.wikidata.org/sparql",lang:str="en"):
        """
        Fetches all Wikidata properties available 
        in the specified language.

        Returns:
            list: A list of dictionaries, each containing the ID, label, and description of a property.
        """
        self.sparql = SPARQL(endpoint_url)
        query=Prefixes.getPrefixes(["wikibase","rdfs","schema"])
        query += f"""
SELECT ?property ?wbType ?propertyLabel ?propertyDescription WHERE {{
  ?property a wikibase:Property;
  rdfs:label ?propertyLabel;
  schema:description ?propertyDescription.
  ?property wikibase:propertyType  ?wbType.
  FILTER(LANG(?propertyLabel) = "{lang}").
  FILTER(LANG(?propertyDescription) = "{lang}").
}}
        """
        results = self.sparql.queryAsListOfDicts(query)
        # Initialize or clear the dictionary for the specified language
        self.props[lang] = {}

        # Populate the dictionary
        for result in results:
            pid = result['property'].split('/')[-1]  # Extracts ID from URI
            type_name=result['wbType'].split("#")[-1]
            plabel=result['propertyLabel']
            self.props[lang][plabel] = WikidataProperty(
                pid=pid,
                plabel=plabel,
                description=result['propertyDescription'],
                type_name=type_name,
                lang=lang
            )
        return self.props[lang]
    
    @classmethod
    def get_instance(cls,
        endpoint_url:str="https://qlever.cs.uni-freiburg.de/api/wikidata",
        langs=["en","de","fr"]):
        """
        initialize the wikidata property manager
        
        Args:
            endpoint_url(str): the SPARQL endpoint to query if there is no cache available
            langs(List[str]): the list of languages to query propery labels and descriptions for
        """
        cache_path = cls.get_cache_path()
        # Check if cache file exists and is not empty
        if os.path.exists(cache_path) and os.path.getsize(cache_path) > 0:
            wpm=cls.from_cache(cache_path)
        else:
            wpm=cls.from_endpoint(endpoint_url, langs)
            wpm.store_to_cache()
        return wpm
    
    @classmethod
    def get_cache_path(cls)->str:
        home = str(Path.home())
        cache_dir = f"{home}/.wikidata"
        os.makedirs(cache_dir,exist_ok=True)
        cache_path= f"{cache_dir}/wikidata_properties.json"
        return cache_path
    
    @classmethod
    def from_endpoint(cls,endpoint_url:str,langs:List[str]):
        wpm=WikidataPropertyManager()
        for lang in langs:
            wpm.fetch_props_for_lang(endpoint_url=endpoint_url,lang=lang)
        return wpm
           
    def store_to_cache(self, cache_path: str = None):
        """
        Stores the current state of the manager to a cache file.

        Args:
            cache_path (str, optional): The path to the cache file. If None, the default cache path is used.
        """
        if cache_path is None:
            cache_path = WikidataPropertyManager.get_cache_path()
        #self.save_to_yaml_file(cache_path)
        self.save_to_json_file(cache_path)

    @classmethod
    def from_cache(cls, cache_path: str = None) -> "WikidataPropertyManager":
        """
        Loads the manager's state from a cache file.

        Args:
            cache_path (str, optional): The path to the cache file. If None, the default cache path is used.

        Returns:
            WikidataPropertyManager: An instance of the manager with the loaded data.
        """
        if cache_path is None:
            cache_path = cls.get_cache_path()
        return cls.load_from_json_file(cache_path)
    
    def get_properties_by_labels(self, labels: List[str], lang: str) -> Dict[str, WikidataProperty]:
        """
        Get properties by their labels for a specific language.
        
        Args:
            labels: List of property labels to search for.
            lang: The language of the labels.
        
        Returns:
            A dictionary of {label: WikidataProperty} for found properties.
        """
        matched_properties = {}
        # Check if language exists in cached properties
        if lang in self.props:
            # Iterate over requested labels and try to find them in the cached properties
            for label in labels:
                for prop_label, prop in self.props[lang].items():
                    if label.lower() == prop_label.lower():
                        matched_properties[label] = prop
                        break  # Assume unique labels, break after first match
        return matched_properties
    
    def get_properties_by_ids(self, ids: List[str], lang: str) -> Dict[str, Optional[WikidataProperty]]:
        """
        Get properties by their IDs for a specific language.

        Args:
            ids: List of property IDs to search for.
            lang: The language of the properties.

        Returns:
            A dictionary of {property ID: WikidataProperty or None} for found and not found properties.
        """
        matched_properties = {}
        if lang in self.props_by_id:
            for pid in ids:
                matched_properties[pid] = self.props_by_id[lang].get(pid)
        return matched_properties
    
    def get_property_by_id(self, property_id: str, lang: str = "en") -> WikidataProperty:
        """
        lookup a WikidataProperty for the given property_id

        Args:
            property_id(str): a property ID e.g. "P6375"
            lang(str): the language for the label
        """
        properties = self.get_properties_by_ids([property_id], lang)
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
        property_type_enum (WdDatatype): The enum representation of the property type, initialized based on propertyType.
        qualifierOf (Optional[str]): Specifies if the property is a qualifier of another property.
        valueLookupType (Optional[Any]): The type (instance of/P31) of the property value for lookup if the value is not already a QID.
        value (Optional[Any]): The default value to set for the property.
        varname (Optional[str]): An optional variable name for internal use.

    The __post_init__ method ensures the propertyType is correctly interpreted and stored as both a string and an enum.
    """
    propertyName: str
    propertyId: str
    propertyType: str
    
    #property_type_enum: WdDatatype=field(init=False)
    column: Optional[str]=None  # if None, the value is used
    qualifierOf: str = None
    valueLookupType: Any = None  # type (instance of/P31) of the property value → used to lookup the qid if property value if value is not already a qid
    value: Any = None  # set this value for the property
    varname: str = None
    
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
    def from_records(
        cls, prop_mapping_records: Dict[str, dict]
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
            mapping = PropertyMapping.from_record(record)
            mappings.append(mapping)
        return mappings

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
                props=wpm.get_properties_by_ids([pid], "en")
                if len(props==1):
                    prop=props[0]
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
        is_item_id= self.property_type_enum is WdDatatype.itemid
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