"""
Created on 2022-04-30

@author: wf
"""
import pprint
from typing import List, Optional

from lodstorage.lod import LOD
from lodstorage.sparql import SPARQL

from ez_wikidata.wbquery import WikibaseQuery
from ez_wikidata.wikidata import PropertyMapping, WdDatatype
from tests.basetest import BaseTest


class TestWikibaseQuery(BaseTest):
    """
    test the Wikibase Query
    """

    def setUp(self, debug=False, profile=True):
        BaseTest.setUp(self, debug=debug, profile=profile)
        self.endpointUrl = "https://query.wikidata.org/sparql"

    def testSingleQuoteHandlingIssue4(self):
        """
        see https://github.com/WolfgangFahl/PyGenericSpreadSheet/issues/4
        """
        debug = self.debug
        # debug=True
        url = "https://docs.google.com/spreadsheets/d/1AZ4tji1NDuPZ0gwsAxOADEQ9jz_67yRao2QcCaJQjmk"
        sheetName = "WorldPrayerDay"
        entityName = "WorldPrayerDay"
        _query, sparqlQuery = WikibaseQuery.sparqlOfGoogleSheet(
            url, sheetName, entityName, pkColumn="Theme", debug=debug
        )
        if debug:
            print(sparqlQuery)
        wpdlist = self.getSparqlResult(sparqlQuery, debug)
        if wpdlist:
            self.assertTrue(len(wpdlist) > 90)
        self.assertTrue("God\\'s Wisdom" in sparqlQuery)

    def getContinentQuery(self, pkColumn: "item", debug: bool = False):
        url = "https://docs.google.com/spreadsheets/d/1ciz_hvLpPlSm_Y30HapuERBOyRBh-NC4UFxKOBU49Tw"
        sheetName = "Continent"
        entityName = sheetName
        wbQuery, sparqlQuery = WikibaseQuery.sparqlOfGoogleSheet(
            url, sheetName, entityName, pkColumn=pkColumn, debug=debug
        )
        clist = self.getSparqlResult(sparqlQuery, debug)
        return wbQuery, sparqlQuery, clist

    def getSparqlResult(
        self, sparqlQuery: str, debug: bool = False
    ) -> Optional[List[dict]]:
        """
        Get Query result as LoD from given query

        Args:
            sparqlQuery: SPARQl query string
            debug: If TRUE print query and result

        Returns:
            List[dict]: query result
            None: if endpointUrl is not defined
        """
        rows = None
        if debug:
            print(sparqlQuery)
        if self.endpointUrl:
            sparql = SPARQL(self.endpointUrl)
            rows = sparql.queryAsListOfDicts(sparqlQuery)
            if debug:
                pprint.pprint(rows)
        return rows

    def testSupportFormatterUrisForExternalIdentifiersIssue5(self):
        """
        see https://github.com/WolfgangFahl/PyGenericSpreadSheet/issues/5

        support formatter URIs for external identifiers #5
        """
        debug = self.debug
        pkColumn = "LoCId"
        # debug=True
        _wbQuery, sparqlQuery, clist = self.getContinentQuery(pkColumn, debug=debug)
        self.assertTrue(len(clist) >= 5)
        self.assertTrue("BIND(IRI(REPLACE(" in sparqlQuery)

    def testAllowItemsAsValuesInGetValuesClause(self):
        """
        allow items as values in getValuesClause
        see https://github.com/WolfgangFahl/PyGenericSpreadSheet/issues/6
        """
        pkColumn = "LoCId"
        debug = self.debug
        # debug=True
        wbQuery, _sparqlQuery, clist = self.getContinentQuery(pkColumn, debug=debug)
        self.assertTrue(len(clist) >= 5)
        continentsByItem, _dup = LOD.getLookup(clist, "item")
        if debug:
            pprint.pprint(continentsByItem)
        pkProp = "item"
        valuesClause = wbQuery.getValuesClause(
            continentsByItem.keys(), pkProp, propType=""
        )
        sparqlQuery = wbQuery.asSparql(
            filterClause=valuesClause, orderClause=f"ORDER BY ?{pkProp}", pk=pkProp
        )
        continentRows = self.getSparqlResult(sparqlQuery, debug)
        if self.debug:
            print(continentRows)
        self.assertTrue("wd:Q15" in sparqlQuery)
