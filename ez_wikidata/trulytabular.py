"""
Created on 2022-04-14

@author: wf
"""
import datetime
import logging
import os
from pathlib import Path
from typing import Union

from lodstorage.query import Endpoint, Query, QueryManager, YamlPath
from lodstorage.sparql import SPARQL
from lodstorage.version import Version
from ez_wikidata.wdproperty import WikidataProperty, WikidataPropertyManager
from ez_wikidata.wikidata import WikidataItem
from ez_wikidata.prefixes import Prefixes

class TrulyTabular(object):
    """
    truly tabular SPARQL/RDF analysis

    checks "how tabular" a query based on a list of properties of an itemclass is
    """

    def __init__(
        self,
        itemQid,
        propertyLabels: list = [],
        propertyIds: list = [],
        subclassPredicate="wdt:P31",
        where: str = None,
        endpointConf=None,
        lang="en",
        debug=False,
    ):
        """
        Constructor

        Args:
            itemQid(str): wikidata id of the type to analyze
            propertyLabels(list): a list of labels of properties to be considered
            propertyIds(list): a list of ids of properties to be considered
            subclassPredicate(str): the subclass Predicate to use
            where(str): extra where clause for instance selection (if any)
            endpoint(str): the url of the SPARQL endpoint to be used
        """
        self.itemQid = itemQid
        self.debug = debug
        if endpointConf is None:
            endpointConf = Endpoint.getDefault()
        self.endpointConf = endpointConf
        self.wpm=WikidataPropertyManager.get_instance(endpoint_url=endpointConf.endpoint)
        self.sparql = SPARQL(endpointConf.endpoint, method=self.endpointConf.method)
        self.sparql.debug = self.debug
        self.subclassPredicate = subclassPredicate
        self.where = f"\n  {where}" if where is not None else ""
        self.lang = lang
        self.item = WikidataItem(
            itemQid, sparql=self.sparql, lang=lang, debug=self.debug
        )
        self.queryManager = TrulyTabular.getQueryManager(debug=self.debug)
        self.properties = self.wpm.get_properties_by_ids(
            propertyIds, lang
        )
        self.properties.update(
            self.wpm.get_properties_by_labels(propertyLabels, lang)
        )
        self.isodate = datetime.datetime.now().isoformat()
        self.error = None

    def __str__(self):
        """
        Returns:
            str: my text representation
        """
        return self.asText(long=False)

    def count(self):
        """
        get my count
        """
        itemText = self.getItemText()
        query = f"""# Count all items with the given type
# {itemText}
{Prefixes.getPrefixes()}
SELECT (COUNT (DISTINCT ?item) AS ?count)
WHERE
{{
  # instance of {self.item.qlabel}
  ?item {self.subclassPredicate} wd:{self.item.qid}.{self.where}
}}"""
        try:
            count = self.sparql.getValue(query, "count")
            # workaround https://github.com/ad-freiburg/qlever/issues/717
            count = int(count)
        except Exception as ex:
            self.error = ex
            count = None

        return count, query

    def asText(self, long: bool = True):
        """
        returns my content as a text representation

        Args:
            long(bool): True if a long format including url is wished

        Returns:
            str: a text representation of my content
        """
        text = self.item.asText(long)
        return text

    def getItemText(self):
        # leads to 405 Method not allowed in SPARQLWrapper under certain circumstances
        # itemText=self.asText(long=True)
        itemText = f"{self.itemQid}:{self.item.qlabel}"
        return itemText

    @classmethod
    def getQueryManager(cls, lang="sparql", name="trulytabular", debug=False):
        """
        get the query manager for the given language and fileName

        Args:
            lang(str): the language of the queries to extract
            name(str): the name of the manager containing the query specifications
            debug(bool): if True set debugging on
        """
        qYamlFileName = f"{name}.yaml"
        for qYamlFile in YamlPath.getPaths(qYamlFileName):
            if os.path.isfile(qYamlFile):
                qm = QueryManager(lang=lang, debug=debug, queriesPath=qYamlFile)
                return qm
        return None

    def generateSparqlQuery(
        self,
        genMap: dict,
        listSeparator: str = "⇹",
        naive: bool = True,
        lang: str = "en",
    ) -> str:
        """
        generate a SPARQL Query

        Args:
            genMap(dict): a dictionary of generation items aggregates/ignores/labels
            listSeparator(str): the symbole to use as a list separator for GROUP_CONCAT
            naive(bool): if True - generate a naive straight forward SPARQL query
                if False generate a proper truly tabular aggregate query
            lang(str): the language to generate for

        Returns:
            str: the generated SPARQL Query
        """
        # The Wikidata item to generate the query for
        item = self.item
        # the name of this script
        script = Path(__file__).name
        # the mode of generation
        naiveText = "naive" if naive else "aggregate"
        # start with th preamble and PREFIX section
        # select the item and it's label
        sparqlQuery = f"""# truly tabular {naiveText} query for 
# {item.qid}:{item.qlabel}
# generated by {script} version {Version.version} on {self.isodate}
{Prefixes.getPrefixes()}
SELECT ?{item.itemVarname} ?{item.labelVarname}"""
        # loop over all properties
        for wdProp in self.properties.values():
            if naive:
                sparqlQuery += f"\n  ?{wdProp.valueVarname}"
            else:
                if wdProp.pid in genMap:
                    genList = genMap[wdProp.pid]
                    for aggregate in genList:
                        if not aggregate in ["ignore", "label"]:
                            distinct = ""
                            if aggregate == "list":
                                aggregateFunc = "GROUP_CONCAT"
                                aggregateParam = f';SEPARATOR="{listSeparator}"'
                                distinct = "DISTINCT "
                            else:
                                if aggregate == "count":
                                    distinct = "DISTINCT "
                                aggregateFunc = aggregate.upper()
                                aggregateParam = ""
                            sparqlQuery += f"\n  ({aggregateFunc} ({distinct}?{wdProp.valueVarname}{aggregateParam}) AS ?{wdProp.valueVarname}_{aggregate})"
                        elif aggregate == "label":
                            sparqlQuery += f"\n  ?{wdProp.labelVarname}"
                        elif aggregate == "ignore" and not "label" in genList:
                            sparqlQuery += f"\n  ?{wdProp.valueVarname}"
        sparqlQuery += f"""
WHERE {{
  # instanceof {item.qid}:{item.qlabel}
  ?{item.itemVarname} {self.subclassPredicate} wd:{item.qid}.
  # label
  ?{item.itemVarname} rdfs:label ?{item.labelVarname}.  
  FILTER (LANG(?{item.labelVarname}) = "{lang}").
"""
        for wdProp in self.properties.values():
            sparqlQuery += f"""  # {wdProp}
  OPTIONAL {{ 
    ?{item.itemVarname} wdt:{wdProp.pid} ?{wdProp.valueVarname}. """
            if wdProp.pid in genMap:
                genList = genMap[wdProp.pid]
                if "label" in genList:
                    sparqlQuery += f"""\n    ?{wdProp.valueVarname} rdfs:label ?{wdProp.labelVarname}."""
                    sparqlQuery += (
                        f"""\n    FILTER (LANG(?{wdProp.labelVarname}) = "{lang}")."""
                    )
            sparqlQuery += "\n  }\n"
        # close where Clause
        sparqlQuery += """}\n"""
        # optionally add Aggregate
        if not naive:
            sparqlQuery += f"""GROUP BY
  ?{item.itemVarname} 
  ?{item.labelVarname}
"""
            for wdProp in self.properties.values():
                if wdProp.pid in genMap:
                    genList = genMap[wdProp.pid]
                    if "label" in genList:
                        sparqlQuery += f"\n  ?{wdProp.labelVarname}"
                    if "ignore" in genList and not "label" in genList:
                        sparqlQuery += f"\n  ?{wdProp.valueVarname}"
            havingCount = 0
            havingDelim = "   "
            for wdProp in self.properties.values():
                if wdProp.pid in genMap:
                    genList = genMap[wdProp.pid]
                    if "ignore" in genList:
                        havingCount += 1
                        if havingCount == 1:
                            sparqlQuery += f"\nHAVING ("

                        sparqlQuery += (
                            f"\n  {havingDelim}COUNT(?{wdProp.valueVarname})<=1"
                        )
                        havingDelim = "&& "
            if havingCount > 0:
                sparqlQuery += f"\n)"
        return sparqlQuery

    def mostFrequentPropertiesQuery(self, whereClause: str = None, minCount: int = 0):
        """
        get the most frequently used properties

        Args:
            whereClause(str): an extra WhereClause to use
        """
        if whereClause is None:
            whereClause = f"?item {self.subclassPredicate} wd:{self.itemQid}"
            if self.endpointConf.database != "qlever":
                whereClause += ";?p ?id"
        whereClause += "."
        minCountFilter = ""
        if minCount > 0:
            minCountFilter = f"\n  FILTER(?count >{minCount})."
        itemText = self.getItemText()
        sparqlQuery = f"""# get the most frequently used properties for
# {itemText}
{Prefixes.getPrefixes()}
SELECT ?prop ?propLabel ?wbType ?count WHERE {{
  {{"""
        if self.endpointConf.database == "qlever":
            sparqlQuery += f"""
    SELECT ?p (COUNT(DISTINCT ?item) AS ?count) WHERE {{"""
        else:
            sparqlQuery += f"""
    SELECT ?prop (COUNT(DISTINCT ?item) AS ?count) WHERE {{"""
        if self.endpointConf.database == "blazegraph":
            sparqlQuery += f"""
      hint:Query hint:optimizer "None"."""
        sparqlQuery += f"""
      {whereClause}"""
        if self.endpointConf.database == "qlever":
            sparqlQuery += f"""  
      ?item ql:has-predicate ?p 
    }} GROUP BY ?p
  }}
  ?prop wikibase:directClaim ?p."""
        else:
            sparqlQuery += f"""
      ?prop wikibase:directClaim ?p.
    }}
    GROUP BY ?prop ?propLabel
  }}"""
        sparqlQuery += f"""
  ?prop rdfs:label ?propLabel.
  ?prop wikibase:propertyType ?wbType.
  FILTER(LANG(?propLabel) = "{self.lang}").{minCountFilter}  
}}
ORDER BY DESC (?count)
"""
        title = f"most frequently used properties for {self.item.asText(long=True)}"
        query = Query(
            name=f"mostFrequentProperties for {itemText}",
            query=sparqlQuery,
            title=title,
        )
        return query

    def noneTabularQuery(self, wdProperty: WikidataProperty, asFrequency: bool = True):
        """
        get the none tabular entries for the given property

        Args:
            wdProperty(WikidataProperty): the property to analyze
            asFrequency(bool): if true do a frequency analysis
        """
        propertyLabel = wdProperty.plabel
        propertyId = wdProperty.pid
        # work around https://github.com/RDFLib/sparqlwrapper/issues/211
        if "described at" in propertyLabel:
            propertyLabel = propertyLabel.replace("described at", "describ'd at")
        sparql = f"""SELECT ?item ?itemLabel (COUNT (?value) AS ?count)
WHERE
{{
  # instance of {self.item.qlabel}
  ?item {self.subclassPredicate} wd:{self.itemQid}.{self.where}
  ?item rdfs:label ?itemLabel.
  FILTER (LANG(?itemLabel) = "{self.lang}").
  # {propertyLabel}
  ?item {wdProperty.getPredicate()} ?value.
}} GROUP BY ?item ?itemLabel
"""
        if asFrequency:
            freqDesc = "frequencies"
            sparql = f"""SELECT ?count (COUNT(?count) AS ?frequency) WHERE {{{{
{sparql}
}}}}
GROUP BY ?count
ORDER BY DESC (?frequency)"""
        else:
            freqDesc = "records"
            sparql = f"""{sparql}
HAVING (COUNT (?value) > 1)
ORDER BY DESC(?count)"""
        itemText = self.getItemText()
        sparql = (
            f"""# Count all {itemText} items
# with the given {propertyLabel}({propertyId}) https://www.wikidata.org/wiki/Property:{propertyId} 
{Prefixes.getPrefixes()}
"""
            + sparql
        )
        title = f"non tabular entries for {self.item.qlabel}/{propertyLabel}:{freqDesc}"
        name = f"NonTabular {self.item.qlabel}/{propertyLabel}:{freqDesc}"
        query = Query(query=sparql, name=name, title=title)
        return query

    def noneTabular(self, wdProperty: WikidataProperty):
        """
        get the none tabular result for the given Wikidata property

        Args:
            wdProperty(WikidataProperty): the Wikidata property
        """
        query = self.noneTabularQuery(wdProperty)
        if self.debug:
            logging.info(query.query)
        qlod = self.sparql.queryAsListOfDicts(query.query)
        return qlod

    def addStatsColWithPercent(
        self, m: dict, col: str, value: Union[int, float], total: Union[int, float]
    ):
        """
        add a statistics Column
        Args:
            m(dict):
            col(str): name of the column
            value: value
            total: total value
        """
        m[col] = value
        if total is not None and total > 0:
            m[f"{col}%"] = float(f"{value/total*100:.1f}")
        else:
            m[f"{col}%"] = None

    def genWdPropertyStatistic(
        self, wdProperty: WikidataProperty, itemCount: int, withQuery=True
    ) -> dict:
        """
        generate a property Statistics Row for the given wikidata Property

        Args:
            wdProperty(WikidataProperty): the property to get the statistics for
            itemCount(int): the total number of items to check
            withQuery(bool): if true include the sparql query

        Returns:
            dict: a statistics row
        """
        ntlod = self.noneTabular(wdProperty)
        statsRow = {"property": wdProperty.plabel}
        total = 0
        nttotal = 0
        maxCount = 0
        for record in ntlod:
            f = int(record["frequency"])
            count = int(record["count"])
            # statsRow[f"f{count}"]=f
            if count > 1:
                nttotal += f
            else:
                statsRow["1"] = f
            if count > maxCount:
                maxCount = count
            total += f
        statsRow["maxf"] = maxCount
        if withQuery:
            statsRow["queryf"] = self.noneTabularQuery(wdProperty).query
            statsRow["queryex"] = self.noneTabularQuery(
                wdProperty, asFrequency=False
            ).query
        self.addStatsColWithPercent(statsRow, "total", total, itemCount)
        self.addStatsColWithPercent(statsRow, "non tabular", nttotal, total)
        return statsRow

    def genPropertyStatistics(self):
        """
        generate the property Statistics

        Returns:
            generator: a generator of statistic dict rows
        """
        itemCount, _itemCountQuery = self.count()
        for wdProperty in self.properties.values():
            statsRow = self.genWdPropertyStatistic(wdProperty, itemCount)
            yield statsRow

    def getPropertyStatistics(self):
        """
        get the property Statistics
        """
        itemCount, _itemCountQuery = self.count()
        lod = [{"property": "∑", "total": itemCount, "total%": 100.0}]
        for wdProperty in self.properties.values():
            statsRow = self.genWdPropertyStatistic(wdProperty, itemCount)
            lod.append(statsRow)
        return lod
