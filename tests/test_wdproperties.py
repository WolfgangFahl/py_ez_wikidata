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
        
    def test_WikidataPropertiesManager(self):
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
            
    def test_get_properties_by_labels(self):
        """
        Test the retrieval of properties by labels.
        """
        # Test data: labels in different languages and the expected number of matches
        test_cases = [
            (['Einwohnerzahl'], 'de','P1082'),  # German for 'population'
            (['population'], 'en','P1082'),  # English
            (['population'], 'fr', 'P1082')   # French
            
        ]

        for labels, lang, expected_pid in test_cases:
            properties = self.wpm.get_properties_by_labels(labels, lang)
            msg=f"Failed for labels {labels} in language {lang}"
            self.assertEqual(1, len(properties), msg)
            plabel=labels[0]
            self.assertIn(plabel, properties, msg)
            prop=properties[plabel]
            self.assertEqual(expected_pid,prop.pid)

    def test_get_properties_by_ids(self):
        """
        Test the retrieval of properties by IDs.
        """
        # Test data: property IDs and the expected number of matches
        test_cases = [
            (['P1082','P17'], 'en', ["population","country"]),  
            (['P1082','P276'], 'de', ["Einwohnerzahl","Ort"]),
            (['P1082'], 'fr', ["population"])
        ]

        for ids, lang, expected_labels in test_cases:
            properties = self.wpm.get_properties_by_ids(ids, lang)
            self.assertEqual(len(properties), len(expected_labels), f"Failed for IDs {ids} in language {lang}")

            # Additionally, check if the retrieved properties match the expected ID
            index=0
            for prop_id, prop in properties.items():
                self.assertIsNotNone(prop, f"Property {prop_id} should not be None")
                self.assertEqual(prop.pid, prop_id, f"Retrieved property ID {prop.pid} does not match expected {prop_id}")
                self.assertEqual(prop.plabel,expected_labels[index])
                index+=1