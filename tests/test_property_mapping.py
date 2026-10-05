"""
Created on 2023-01-14

@author: wf
"""

from ez_wikidata.wdproperty import (
    PropertyMapping,
    PropertyMappings,
    WdDatatype,
    WikidataPropertyManager,
)
from tests.basetest import BaseTest


class TestPropertyMapping(BaseTest):
    """
    test the property Mapping
    """

    def setUp(self, debug=False, profile=True):
        BaseTest.setUp(self, debug=debug, profile=profile)
        self.wpm = WikidataPropertyManager.get_instance()

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
                    mapping = PropertyMapping.from_record(wpm=self.wpm, record=rec)
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

    def test_bundled_mappings_consistent(self):
        """
        test that in every bundled mapping the propertyId resolves to the
        propertyName - a mismatched pair would silently write a wrong claim
        e.g. researchGate with P6178 (Dimensions author ID) instead of P2038
        """
        for name in ["scholar", "extension", "paper", "proceedings", "event"]:
            property_mappings = PropertyMappings.of_name(name)
            for column, mapping in property_mappings.mappings.items():
                if mapping.propertyId is None or mapping.propertyName is None:
                    continue
                with self.subTest(mapping=f"{name}.{column}"):
                    wd_property = self.wpm.get_property_by_id(mapping.propertyId)
                    self.assertIsNotNone(
                        wd_property,
                        f"{name}.{column}: unknown property {mapping.propertyId}",
                    )
                    self.assertEqual(
                        mapping.propertyName,
                        wd_property.plabel,
                        f"{name}.{column}: {mapping.propertyId} is '{wd_property.plabel}' not '{mapping.propertyName}'",
                    )

    def test_DefaultItemPropertyMapping(self):
        """
        test the default item PropertyMapping
        """
        itemMapping = PropertyMapping.getDefaultItemPropertyMapping()
        self.assertIsNotNone(itemMapping)
        self.assertTrue(isinstance(itemMapping, PropertyMapping))
        self.assertTrue(itemMapping.is_item_itself())

    def test_scholar_mapping(self):
        """
        test loading the bundled Scholar PropertyMappings (resources/scholar_props.yaml)
        used to create a brand-new Wikidata entry for a scholar
        """
        scholar = PropertyMappings.of_name("scholar")
        self.assertEqual("scholar_props", scholar.name)
        # instance of human is fixed
        self.assertEqual("P31", scholar.mappings["instanceof"].propertyId)
        self.assertEqual("Q5", scholar.mappings["instanceof"].value)
        # scholarly identifiers documented in Template:Scholar
        expected = {
            "orcid": "P496",
            "dblp": "P2456",
            "gnd": "P227",
            "googleScholarUser": "P1960",
            "homepage": "P856",
            "linkedInId": "P6634",
            "researchGate": "P2038",
            "occupation": "P106",
        }
        for column, pid in expected.items():
            self.assertEqual(pid, scholar.mappings[column].propertyId)
        # EntitySchema cross-reference (P12861) round-trips as entity_schema
        self.assertEqual(
            WdDatatype.entity_schema, scholar.mappings["shacl"].property_type_enum
        )

    def test_paper_mapping(self):
        """
        test loading the bundled Paper PropertyMappings (resources/paper_props.yaml)
        used to create a Wikidata entry for a scholarly article - see issue #14
        """
        paper = PropertyMappings.of_name("paper")
        self.assertEqual("paper_props", paper.name)
        # instance of scholarly article is fixed
        self.assertEqual("P31", paper.mappings["instanceof"].propertyId)
        self.assertEqual("Q13442814", paper.mappings["instanceof"].value)
        expected = {
            "title": "P1476",
            "author": "P50",
            "series_ordinal": "P1545",
            "language": "P407",
            "publication_date": "P577",
            "published_in": "P1433",
            "pages": "P304",
            "doi": "P356",
            "dblp": "P8978",
            "full_text_url": "P953",
        }
        for column, pid in expected.items():
            self.assertEqual(pid, paper.mappings[column].propertyId)
        # the series ordinal qualifies the author statement
        self.assertEqual("author", paper.mappings["series_ordinal"].qualifierOf)

    def test_proceedings_and_event_mapping(self):
        """
        test loading the bundled proceedings and event PropertyMappings used
        for CEUR-WS volumes by pyCEURmake wikidatasync - see issue #17
        """
        proceedings = PropertyMappings.of_name("proceedings")
        self.assertEqual("proceedings_props", proceedings.name)
        self.assertEqual("Q1143604", proceedings.mappings["instanceof"].value)
        self.assertEqual("Q27230297", proceedings.mappings["part of the series"].value)
        expected = {
            "volume": ("P478", "part of the series"),
            "short name": ("P1813", None),
            "pubDate": ("P577", None),
            "title": ("P1476", None),
            "ceurwsUrl": ("P973", None),
            "language of work or name": ("P407", "ceurwsUrl"),
            "fullWorkUrl": ("P953", None),
            "urn": ("P4109", None),
        }
        for column, (pid, qualifier_of) in expected.items():
            mapping = proceedings.mappings[column]
            self.assertEqual(pid, mapping.propertyId)
            self.assertEqual(qualifier_of, mapping.qualifierOf)
        event = PropertyMappings.of_name("event")
        self.assertEqual("event_props", event.name)
        # the class of the event comes from the record
        self.assertIsNone(event.mappings["instanceof"].value)
        expected = {
            "short name": "P1813",
            "title": "P1476",
            "describedAt": "P973",
            "language of work or name": "P407",
            "dblpEventId": "P10692",
            "start time": "P580",
            "end time": "P582",
            "locationWikidataId": "P276",
            "countryWikidataId": "P17",
        }
        for column, pid in expected.items():
            self.assertEqual(pid, event.mappings[column].propertyId)
        self.assertEqual(
            "describedAt", event.mappings["language of work or name"].qualifierOf
        )
