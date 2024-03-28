"""
Created on 2024-03-01

@author: wf
"""
from ez_wikidata.wbquery import WikibaseQuery
from tests.basetest import BaseTest


class TestWikibaseQuery(BaseTest):
    """
    test the WikibaseQuery module
    """

    def setUp(self, debug=False, profile=True):
        super().setUp(debug, profile)

    def test_init(self):
        """Test initialization of WikibaseQuery."""
        query = WikibaseQuery(entity="Q5", debug=True)
        self.assertTrue(query.debug)
        self.assertEqual(query.entity, "Q5")
        self.assertEqual(len(query.propertiesByName), 0)

    def test_addPropertyFromDescriptionRow(self):
        """
        Test adding a property from a description
        row with entity beer and property Country."""
        query = WikibaseQuery(entity="Q44")  # Assuming Q44 is the entity ID for "beer"
        # This example assumes the structure of your row data. Adjust as necessary.
        row = {
            "PropertyName": "country",  # Human-readable name for the property
            "PropertyId": "P17",  # Property ID for "country"
            "Column": "CountryCol",  # The column name where this property's data will be stored or displayed
            "Type": "item",  # Assuming the country is represented as an item in Wikidata
        }
        query.addPropertyFromDescriptionRow(row)

        self.assertIn("country", query.propertiesByName)
        self.assertIn("P17", query.propertiesById)
        self.assertIn("CountryCol", query.propertiesByColumn)
        self.assertIn("country", query.propertiesByVarname)
