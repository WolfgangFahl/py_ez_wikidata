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
    Supported wikidata datatypes
    """

    item = auto()
    itemid = auto()
    year = auto()
    date = auto()
    extid = auto()
    text = auto()
    url = auto()
    string = auto()

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
    lang: str="en" # the language 
    reverse: bool = False  # Indicates if the property is used in reverse direction
    reverse: bool = False  # Indicates if the property is used in reverse direction

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

    @classmethod
    def getPropertiesByLabels(cls, sparql, propertyLabels: list, lang: str = "en"):
        """
        get a list of Wikidata properties by the given label list

        Args:
            sparql(SPARQL): the SPARQL endpoint to use
            propertyLabels(list): a list of labels of the properties
            lang(str): the language of the label
        """
        # the result dict
        wdProperties = {}
        if len(propertyLabels) > 0:
            valuesClause = ""
            for propertyLabel in propertyLabels:
                valuesClause += f'   "{propertyLabel}"@{lang}\n'
            query = f"""# get the properties for the given labels
{Prefixes.getPrefixes(["rdf","rdfs","wikibase"])}
SELECT ?property ?propertyLabel ?wbType WHERE {{
  VALUES ?propertyLabel {{
{valuesClause}
  }}
  ?property rdf:type wikibase:Property;rdfs:label ?propertyLabel.
  ?property wikibase:propertyType  ?wbType.
  FILTER(LANG(?propertyLabel) = "{lang}")
}}"""
            cls.addPropertiesForQuery(wdProperties, sparql, query)
        return wdProperties

    @classmethod
    def from_id(cls, property_id: str, sparql, lang: str = "en") -> "WikidataProperty":
        """
        construct a WikidataProperty from the given property_id

        Args:
            property_id(str): a property ID e.g. "P6375"
            sparql(SPARQL): the SPARQL endpoint to use
            lang(str): the language for the label
        """
        properties = cls.getPropertiesByIds(sparql, [property_id], lang)
        prop_count = len(properties)
        if prop_count == 1:
            return list(properties.values())[0]
        elif prop_count == 0:
            return None
        else:
            property_labels = list(properties.keys())
            msg = f"unexpected from_id result for property id {property_id}. Expected 0 or 1 results bot got:{property_labels}"
            raise ValueError(msg)
        pass

    @classmethod
    def getPropertiesByIds(cls, sparql, propertyIds: list, lang: str = "en"):
        """
        get a list of Wikidata properties by the given id list

        Args:
            sparql(SPARQL): the SPARQL endpoint to use
            propertyIds(list): a list of ids of the properties
            lang(str): the language of the label
        """
        # the result dict
        wdProperties = {}
        if len(propertyIds) > 0:
            valuesClause = ""
            for propertyId in propertyIds:
                valuesClause += f"   wd:{propertyId}\n"
            query = f"""
# get the property for the given property Ids
{Prefixes.getPrefixes(["rdf","rdfs","wd","wikibase"])}
SELECT ?property ?propertyLabel ?wbType WHERE {{
  VALUES ?property {{
{valuesClause}
  }}
  ?property rdf:type wikibase:Property;rdfs:label ?propertyLabel.
  ?property wikibase:propertyType  ?wbType.
  FILTER(LANG(?propertyLabel) = "{lang}")
}}"""
            cls.addPropertiesForQuery(wdProperties, sparql, query)
        return wdProperties

    @classmethod
    def addPropertiesForQuery(cls, wdProperties: list, sparql, query):
        """
          add properties from the given query's result to the given
          wdProperties list using the given sparql endpoint
        Args:
          wdProperties(list): the list of wikidata properties
          sparql(SPARQL): the SPARQL endpoint to use
          query(str): the SPARQL query to perform
        """
        qLod = sparql.queryAsListOfDicts(query)
        for record in qLod:
            url = record["property"]
            pid = re.sub(r"http://www.wikidata.org/entity/(.*)", r"\1", url)
            prop = WikidataProperty(pid)
            prop.plabel = record["propertyLabel"]
            prop.wbtype = record["wbType"]
            prop.url = url
            wdProperties[prop.plabel] = prop
            prop.varname = Variable.validVarName(prop.plabel)
            prop.valueVarname = (
                f"{prop.varname}Item"
                if "WikibaseItem" in prop.wbtype
                else "" f"{prop.varname}"
            )
            prop.labelVarname = f"{prop.varname}"
            pass
        return wdProperties
    
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
SELECT ?property ?propertyLabel ?propertyDescription WHERE {{
  ?property a wikibase:Property;
  rdfs:label ?propertyLabel;
  schema:description ?propertyDescription.
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
            plabel=result['propertyLabel']
            self.props[lang][plabel] = WikidataProperty(
                pid=pid,
                plabel=plabel,
                description=result['propertyDescription'],
                lang=lang
            )
        return self.props[lang]
    
    @classmethod
    def get_cache_path(cls)->str:
        home = str(Path.home())
        cache_dir = f"{home}/.wikidata"
        os.makedirs(cache_dir,exist_ok=True)
        cache_path= f"{cache_dir}/wikidata_properties.json"
        return cache_path
           
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
    property_type_enum=InitVar[WdDatatype]
    column: Optional[str]=None  # if None, the value is used
    qualifierOf: str = None
    valueLookupType: Any = None  # type (instance of/P31) of the property value → used to lookup the qid if property value if value is not already a qid
    value: Any = None  # set this value for the property
    varname: str = None
    
    def __post_init__(self):
        """
        Convert propertyType from string to WdDatatype enum if necessary
        """
        if isinstance(self.propertyType, str):
            try:
                self.propertyType_enum = WdDatatype[self.propertyType]
            except KeyError:
                raise ValueError(f"Invalid property type: {self.propertyType}")
        else:
            self.propertyType_enum = self.propertyType
            # Ensure propertyType is stored as the correct string representation of the enum for YAML compatibility
            self.propertyType = self.propertyType.name
            
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
    def from_record(cls, record: dict) -> "PropertyMapping":
        """
        initialize PropertyMapping from the given record
        Args:
            record: property mapping information

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
                property_type = Wikidata.get_wddatatype_of_property(
                    record.get("propertyId", None)
                )
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
        Returns true if the property mapping links to the existing item
        """
        return self.propertyType == WdDatatype.item

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

   

