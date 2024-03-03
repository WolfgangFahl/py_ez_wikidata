'''
Created on 2024-03-03

@author: wf
'''
from tests.basetest import BaseTest
from ez_wikidata.wdproperty import WikidataPropertyManager, WdDatatype
from ez_wikidata.prefixes import Prefixes
from lodstorage.sparql import SPARQL

class TestWikidataProperties(BaseTest):
    """
    test the Wikidata properties handling
    """

    def setUp(self, debug=True, profile=True):
        """
        setUp the tests cases
        """
        super().setUp(debug, profile)
        self.endpoint_url="https://qlever.cs.uni-freiburg.de/api/wikidata"
        self.sparql = SPARQL(self.endpoint_url)
        self.wpm=WikidataPropertyManager.get_instance()
        
    def testWikidataPropertiesManager(self):
        """
        test the WikidataPropertyManager
        """
        langs=["de","en","fr"]
        for lang in langs:
            self.assertTrue(lang in self.wpm.props)
            self.assertTrue(len(self.wpm.props[lang])>5000)
        
    def test_wikidata_datatypes(self):
        """
        test available wikidata datatypes
        """
        # SPARQL query to get the histogram of property datatypes
        query = Prefixes.getPrefixes(["wikibase", "rdf", "rdfs", "schema"])
        query += """
        SELECT ?wbType (COUNT(?property) AS ?count) WHERE {
          ?property rdf:type wikibase:Property.
          ?property wikibase:propertyType ?wbType.
        } GROUP BY ?wbType
        ORDER BY DESC(?count)
        """
        results = self.sparql.queryAsListOfDicts(query)
        for result in results:
            wb_type_name=result["wbType"]
            wb_type=WdDatatype.from_wb_type_name(wb_type_name)
            count=result["count"]
            print(f"{wb_type_name}:{wb_type}  #{count}")