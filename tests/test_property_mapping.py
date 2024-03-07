"""
Created on 2023-01-14

@author: wf
"""
from ez_wikidata.wdproperty import PropertyMapping, WdDatatype, WikidataPropertyManager
from tests.basetest import BaseTest

class TestPropertyMapping(BaseTest):
    """
    test the property Mapping
    """
    
    def setUp(self, debug=False, profile=True):
        BaseTest.setUp(self, debug=debug, profile=profile)
        self.wpm=WikidataPropertyManager.get_instance()
            

    def test_from_record(self):
        """
        tests from_record
        """
        test_params = [
            (
                "languageOfWork",
                "language of work or name",
                "P407",
                "itemid",
                "official website",
                "",
            )
        ]
        for params in test_params:
            col, name, p_id, p_type, qualifier, lookup = params
            record = {
                "column": col,
                "propertyName": name,
                "propertyType": p_type,
                "propertyId": p_id,
                "qualifierOf": qualifier,
                "valueLookupType": lookup,
            }
            legacy_record = {
                "Column": col,
                "PropertyName": name,
                "PropertyId": p_id,
                "Type": p_type,
                "Qualifier": qualifier,
                "Lookup": lookup,
            }
            for i, rec in enumerate([record, legacy_record]):
                mode = "legacy" if i == 1 else ""
                with self.subTest(f"test parsing from {mode} record", rec=rec):
                    mapping = PropertyMapping.from_record(wpm=self.wpm,record=rec)
                    for key, expected_value in record.items():
                        actual_value = getattr(mapping, key)
                        self.assertEqual(expected_value, actual_value)

    def test_is_qualifier(self):
        """
        tests id_qualifier
        """
        positive_case = PropertyMapping(
            column="volume",
            propertyId="P478",
            propertyName="volume",
            propertyType=WdDatatype.string,
            qualifierOf="part of the series",
        )
        negative_case = PropertyMapping(
            column="acronym",
            propertyId="P1813",
            propertyName="short name",
            propertyType=WdDatatype.text,
        )
        self.assertTrue(positive_case.is_qualifier())
        self.assertFalse(negative_case.is_qualifier())

    def test_WdDatatype_lookup(self):
        """
        tests the WdDatatype lookup for None and empty string as key
        """
        test_params = [(None, WdDatatype.text), ("", WdDatatype.text)]
        for param in test_params:
            with self.subTest(param=param):
                property_type, expected = param
                self.assertEqual(expected, WdDatatype(property_type))

    def test_DefaultItemPropertyMapping(self):
        """
        test the default item PropertyMapping
        """
        itemMapping = PropertyMapping.getDefaultItemPropertyMapping()
        self.assertIsNotNone(itemMapping)
        self.assertTrue(isinstance(itemMapping, PropertyMapping))
        self.assertTrue(itemMapping.is_item_itself())
