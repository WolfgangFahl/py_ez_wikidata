"""
Created on 2022-04-30

@author: wf
"""
import pprint
from typing import Dict, List

from ez_wikidata.wdproperty import WikidataPropertyManager
from ez_wikidata.wikidata import PropertyMapping, WdDatatype


class WikibaseQuery(object):
    """
    a Query for Wikibase
    """

    def __init__(
        self, entity: str, wpm: WikidataPropertyManager = None, debug: bool = False
    ):
        """
        Constructor

        Args:
            entity(str): the entity this query represents
            debug(bool): if True switch on debugging
        """
        self.debug = debug
        self.entity = entity
        if wpm is None:
            wpm = WikidataPropertyManager.get_instance()
        self.wpm = wpm
        self.propertiesByName = {}
        self.propertiesById = {}
        self.propertiesByVarname = {}
        self.propertiesByColumn = {}
        self.rows = []

    def get_property_mappings(self) -> List[PropertyMapping]:
        """
        Get the property mappings as PropertyMapping list

        Returns:
            List[PropertyMapping]: list of PropertyMappings
        """
        prop_maps = self.wpm.get_mappings_for_records(self.propertiesByColumn)
        return prop_maps

    def get_item_mapping(self) -> PropertyMapping:
        """
        Get the mapping that describes the wikidata entity item
        """
        return PropertyMapping.get_item_mapping(self.get_property_mappings())

    def addPropertyFromDescriptionRow(self, row):
        """
        add a property from the given row

        Args:
            row(dict): the row to add
        """
        self.rows.append(row)
        propName = row["PropertyName"]
        propId = row["PropertyId"]
        column = row["Column"]
        # properties might contain blank - replace for SPARQL variable names
        propVarname = row.get("PropVarname", propName)
        propVarname = propVarname.replace(" ", "_")
        propVarname = propVarname.replace("-", "_")
        row["PropVarname"] = propVarname
        # set the values of the lookups
        self.propertiesByName[propName] = row
        self.propertiesByColumn[column] = row
        self.propertiesById[propId] = row
        self.propertiesByVarname[propVarname] = row

    def getColumnTypeAndVarname(self, propName: str) -> (str, str, str):
        """
        get a signature tuple consisting of columnName, propertType and SPARQL variable Name for the given property Name

        Args:
            propName(str): the name of the property

        Raises:
            Exception: if property name is not known

        Returns:
            column,propType,varName tupel
        """
        if propName in self.propertiesByName:
            propRow = self.propertiesByName[propName]
            column = propRow["Column"]
            propType = propRow["Type"]
            varName = propRow["PropVarname"]
            if propType == "item" and varName in [None, ""]:
                varName = "item"
        else:
            raise Exception(
                f"unknown property name {propName} for entity {self.entity}"
            )
        return column, propType, varName

    def inFilter(
        self, values: list, propName: str = "short_name", lang: str = "en"
    ) -> str:
        """
        create a SPARQL IN filter clause

        Args:
            values(list): the list of values to filter for
            propName(str): the property name to filter with
            lang(str): the language to apply
        """
        filterClause = f"\n  FILTER(?{propName} IN("
        delim = ""
        for value in values:
            filterClause += f"{delim}\n    '{value}'@{lang}"
            delim = ","
        filterClause += "\n  ))."
        return filterClause

    def getValuesClause(
        self,
        values: list,
        propVarname: str = "short_name",
        propType: str = "text",
        lang: str = None,
        ignoreEmpty: bool = True,
        wbPrefix: str = "http://www.wikidata.org/entity/",
    ):
        """
        create a SPARQL Values clause

        Args:
            values(list): the list of values to create values for
            propVarname(str): the property variable name to assign the values for
            propType:
            lang: language of labels to query
            ignoreEmpty(bool): ignore empty values if True
            wbPrefix(str): a wikibase/wikidata prefix to be removed for items values
        Returns:
            str: the SPARQL values clause
        """
        valuesClause = f"\n  VALUES(?{propVarname}) {{"
        if lang is not None and propType == "text":
            lang = f"@{lang}"
        else:
            lang = ""
        for value in values:
            if value or not ignoreEmpty:
                if propType in ["item", "itemid", "", None]:
                    if value and value.startswith(wbPrefix):
                        value = value.replace(wbPrefix, "")
                    valuesClause += f"\n   ( wd:{value} )"
                else:
                    if isinstance(value, str):
                        # escape single quotes
                        value = value.replace("'", "\\'")
                        valuesClause += f"\n  ( '{value}'{lang} )"
                    else:
                        valuesClause += f"\n  ( {str(value)} )"
        valuesClause += "\n  }."
        return valuesClause

    def asSparql(
        self,
        filterClause: str = None,
        orderClause: str = None,
        pk: str = None,
        lang: str = "en",
    ) -> str:
        """
        get the sparqlQuery for this query optionally applying a filterClause

        Args:
            filterClause(str): a filter to be applied (if any)
            orderClause(str): an orderClause to be applied (if any)
            pk(str): primaryKey (if any)
            lang(str): the language to be used for labels
        """
        item_mapping = self.get_item_mapping()
        item_varname = item_mapping.varname
        sparql = f"""# 
# get {self.entity} records 
#  
PREFIX pq: <http://www.wikidata.org/prop/qualifier/>
PREFIX p: <http://www.wikidata.org/prop/>
PREFIX schema: <http://schema.org/>
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?{item_varname} ?{item_varname}Label ?{item_varname}Description
"""
        for prop_map in self.get_property_mappings():
            if prop_map.is_item_itself():
                continue
            if not prop_map.value and prop_map.varname:
                property_selections = f"\n  ?{prop_map.varname}"
                if prop_map.property_type_enum is WdDatatype.itemid:
                    # items will automatically fetch labels
                    property_selections += f" ?{prop_map.varname}Label"
                elif prop_map.property_type_enum is WdDatatype.extid:
                    # extid' will automatically fetch formatted URIs
                    property_selections += f" ?{prop_map.varname}Url"
                sparql += property_selections
        query_item_label = f"""?{item_varname} rdfs:label ?{item_varname}Label. FILTER(LANG(?{item_varname}Label) = "{lang}")"""
        query_item_desc = f"""?{item_varname} schema:description ?{item_varname}Description. FILTER(LANG(?{item_varname}Description) = "{lang}")"""
        sparql += f"""\nWHERE {{
    {query_item_label}
    OPTIONAL {{
        {query_item_desc}
    }}
"""
        for prop_map in self.get_property_mappings():
            if prop_map.propertyId in [None, ""]:
                continue
            if prop_map.value:
                # value predefined for property
                sparql += f"\n  ?{item_varname} wdt:{prop_map.propertyId} wd:{prop_map.value}."
            else:
                if prop_map.varname:
                    # primary keys are not optional
                    optional = pk is None or not prop_map.propertyName == pk
                    if optional:
                        sparql += "\n  OPTIONAL {"
                    sparql += f"\n    ?{item_varname} wdt:{prop_map.propertyId} ?{prop_map.varname}."
                    if prop_map.property_type_enum is WdDatatype.itemid:
                        # also query label of the qid with language lang
                        sparql += f"\n    ?{prop_map.varname} rdfs:label ?{prop_map.varname}Label."
                        sparql += f"""\n    FILTER(LANG(?{prop_map.varname}Label) = "{lang}")"""
                    elif prop_map.property_type_enum is WdDatatype.extid:
                        # ToDo: decision to make see https://github.com/WolfgangFahl/PyGenericSpreadSheet/issues/15
                        sparql += f"\n    wd:{prop_map.propertyId} wdt:P1630 ?{prop_map.varname}FormatterUrl."
                        sparql += f"\n    BIND(IRI(REPLACE(?{prop_map.varname}, '^(.+)$', ?{prop_map.varname}FormatterUrl)) AS ?{prop_map.varname}Url)."
                    if optional:
                        sparql += "\n  }"
        if filterClause is not None:
            sparql += f"\n{filterClause}"
        sparql += "\n}"
        if orderClause is not None:
            sparql += f"\n{orderClause}"
        return sparql

    @classmethod
    def ofMapRows(
        cls, entityMapRows: list, debug: bool = False
    ) -> Dict[str, "WikibaseQuery"]:
        """
        create a dict of wikibaseQueries from the given entityMap list of dicts

        Args:
            entityMapRows(list): a list of dict with row descriptions
            debug(bool): if True switch on debugging
        """
        queries = {}
        entityMapDict = {}
        for row in entityMapRows:
            if "Entity" in row:
                entity = row["Entity"]
                if not entity in entityMapDict:
                    entityMapDict[entity] = {}
                entityRows = entityMapDict[entity]
                if "PropertyName" in row:
                    propertyName = row["PropertyName"]
                    entityRows[propertyName] = row
        if debug:
            pprint.pprint(entityMapDict)
        for entity in entityMapDict:
            wbQuery = WikibaseQuery.ofEntityMap(entity, entityMapDict[entity])
            queries[entity] = wbQuery
        return queries

    @classmethod
    def ofEntityMap(cls, entity: str, entityMap: dict) -> "WikibaseQuery":
        """
        create a WikibaseQuery for the given entity and entityMap

        Args:
            entity(str): the entity name
            entityMap(dict): the entity property descriptions
        Returns:
            WikibaseQuery
        """
        wbQuery = WikibaseQuery(entity)
        for row in entityMap.values():
            wbQuery.addPropertyFromDescriptionRow(row)
        return wbQuery
