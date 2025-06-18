import json
import unittest
import uuid
from datetime import datetime

from lodstorage.lod import LOD
from wikibaseintegrator.datatypes import (
    URL,
    ExternalID,
    Item,
    MonolingualText,
    String,
    Time,
)

from ez_wikidata.wikidata import (
    PropertyMapping,
    PropertyMappings,
    UrlReference,
    WdDatatype,
    Wikidata,
    WikidataItem,
    WikidataResult,
)
from tests.basetest import BaseTest


class TestWikidata(BaseTest):
    """
    test the Wikidata access
    """

    def setUp(self, debug=False, profile=True):
        super().setUp(debug, profile)
        self.wd = Wikidata("https://www.wikidata.org", debug=debug)
        self._test_wd = None

    @property
    def test_wikidata(self) -> Wikidata:
        if self._test_wd is None:
            wd = Wikidata(baseurl="https://test.wikidata.org", debug=self.debug)
            wd.loginWithCredentials()
            self._test_wd = wd
        return self._test_wd

    def testItemLookup(self):
        """
        lookup items
        """
        debug = self.debug
        wd = Wikidata("https://www.wikidata.org", debug=self.debug)
        test_params = [
            ("USA", "Q3624078", "Q30"),
            ("ECIR", "Q47258130", "Q5412436"),
            ("Berlin", "Q515", "Q64"),
        ]
        for test_param in test_params:
            with self.subTest(test_param=test_param):
                name, item_type, expected_qid = test_param
                actual_qid = wd.getItemByName(name, item_type)
                if debug:
                    print(actual_qid)
                self.assertEqual(expected_qid, actual_qid)

    def test_convert_to_claim(self):
        """
        tests convert_to_claim
        """
        acronym = PropertyMapping(
            column="acronym",
            propertyId="P1813",
            propertyName="short name",
            propertyType=WdDatatype.text,
        )
        homepage = PropertyMapping(
            column="homepage",
            propertyId="P856",
            propertyName="official website",
            propertyType=WdDatatype.url,
        )
        inception = PropertyMapping(
            column="inception",
            propertyId="P571",
            propertyName="inception",
            propertyType=WdDatatype.year,
        )
        start_time = PropertyMapping(
            column="startTime",
            propertyId="P580",
            propertyName="start time",
            propertyType=WdDatatype.date,
        )
        issn = PropertyMapping(
            column="issn",
            propertyId="P236",
            propertyName="ISSN",
            propertyType=WdDatatype.extid,
        )
        country = PropertyMapping(
            column="country",
            propertyId="P17",
            propertyName="country",
            propertyType=WdDatatype.itemid,
        )
        volume = PropertyMapping(
            column="volume",
            propertyId="P478",
            propertyName="volume",
            propertyType=WdDatatype.string,
        )
        test_params = [  # (value, expected value, expected  type, property mapping)
            ("AAAI", {"text": "AAAI", "language": "en"}, MonolingualText, acronym),
            ("http://ceur-ws.org/", "http://ceur-ws.org/", URL, homepage),
            (
                "1995",
                {
                    "time": "+1995-01-01T00:00:00Z",
                    "before": 0,
                    "after": 0,
                    "precision": 9,
                    "timezone": 0,
                    "calendarmodel": "http://www.wikidata.org/entity/Q1985727",
                },
                Time,
                inception,
            ),
            (
                "1995-05-04",
                {
                    "time": "+1995-05-04T00:00:00Z",
                    "before": 0,
                    "after": 0,
                    "precision": 11,
                    "timezone": 0,
                    "calendarmodel": "http://www.wikidata.org/entity/Q1985727",
                },
                Time,
                start_time,
            ),
            ("1613-0073", "1613-0073", ExternalID, issn),
            (
                "Q30",
                {"entity-type": "item", "numeric-id": 30, "id": "Q30"},
                Item,
                country,
            ),
            ("1", "1", String, volume),
            ("A", "A", String, volume),
            (1, "1", String, volume),
        ]
        for params in test_params:
            with self.subTest("test statement generation", params=params):
                value, expected_value, expected_type, pm = params
                statement = self.wd.convert_to_claim(value, pm)
                self.assertTrue(isinstance(statement, expected_type))
                self.assertEqual(expected_value, statement.mainsnak.datavalue["value"])

    def test_is_wikidata_item_id(self):
        """
        tests is_wikidata_item_id
        """
        test_params = [("human", False), ("Q5", True), ("P17", False)]
        for param in test_params:
            with self.subTest(param=param):
                value, expected = param
                actual = self.wd.is_wikidata_item_id(value)
                self.assertEqual(expected, actual)

    def test_is_wikidata_property_id(self):
        """
        tests is_wikidata_item_id
        """
        test_params = [("country", False), ("P17", True), ("Q5", False)]
        for param in test_params:
            with self.subTest(param=param):
                value, expected = param
                actual = self.wd.is_wikidata_property_id(value)
                self.assertEqual(expected, actual)

    def test_sanitize_label(self):
        """
        tests sanitize_label
        """
        test_params = [
            ("Hello World", 8, None, "Hello..."),
            ("A" * 255, None, None, "A" * 247 + "..."),
            ("P17", 2, "!", "P!"),
        ]
        for param in test_params:
            with self.subTest(param=param):
                label, limit, postfix, expected = param
                actual = self.wd.sanitize_label(label, limit, postfix)
                self.assertEqual(expected, actual)

    def test_get_record(self):
        """
        tests get_record
        ToDo: add more test cases
        """
        expected = {
            "P31": "Q1143604",
            "P1813": "JIST-WP 2017",
            "P577": datetime(2017, 11, 20).date(),
            "P973": "http://ceur-ws.org/Vol-2000/",
            "P0": None,  # invalid prop id to test invalid key handling
        }
        prop_ids = list(expected.keys())
        actual = self.wd.get_record(
            "Q113543868", prop_ids, include_label=False, include_description=False
        )
        self.assertDictEqual(expected, actual)

    def test_get_record_label(self):
        """
        test get_record with property mapping to extract the label of item links
        """
        pm = PropertyMapping(
            column="country",
            propertyName="country",
            propertyType=WdDatatype.itemid,
            propertyId="P17",
            valueLookupType="Q3624078",
        )
        item_id = "Q64"  # Berlin
        expected = {"country": "Germany"}
        actual = self.wd.get_record(
            item_id,
            property_mappings=[pm],
            include_label=False,
            include_description=False,
            label_for_qids=True,
        )
        self.assertDictEqual(expected, actual)

    def check_add_result(self, result: WikidataResult):
        """
        check the result of an add operation
        """
        if result.debug:
            if len(result.errors) > 0:
                print("Errors")
                for index, error in enumerate(result.errors.values()):
                    print(f"{index+1}:{str(error)}")
            else:
                print(f"created {result.qid}")
                print(result.pretty_item_json)
        self.assertEqual(0, len(result.errors))

    @unittest.skipIf(
        BaseTest.inPublicCI(),
        "Tests querying wikidata which is often blocked on public CI",
    )
    def test_get_item_label(self):
        """
        tests get_item_label
        """
        test_params = [
            ("Q64", "en", "Berlin"),
            ("Q183", "en", "Germany"),
            ("Q183", "de", "Deutschland"),
            ("Q64", "xxx", None),
            (None, "en", None),
            ("Q183", None, "Germany"),
        ]
        for test_param in test_params:
            with self.subTest(test_param=test_param):
                item_id, lang, expected_label = test_param
                actual_label = self.wd.get_item_label(item_id, lang)
                self.assertEqual(expected_label, actual_label)

    @unittest.skipIf(
        BaseTest.inPublicCI(),
        "Tests creating and modifying items. To run in CI setup credentials",
    )
    def test_add_record(self):
        """
        tests add_record by creating an item in test.wikidata.org adding property values.
        Also tests adding property values to existing items.
        """
        debug = self.debug
        debug = True
        wd = Wikidata(baseurl="https://test.wikidata.org", debug=debug)
        wd.loginWithCredentials()
        property_mappings = [
            WikidataSandboxProperties.TEXT,
            WikidataSandboxProperties.ITEM,
            WikidataSandboxProperties.DATE,
            WikidataSandboxProperties.YEAR,
            WikidataSandboxProperties.URL,
            WikidataSandboxProperties.EXT_ID,
            PropertyMapping(
                column="dateQualifier",
                propertyId="P96927",
                propertyName="year sandbox property",
                propertyType=WdDatatype.year,
                qualifierOf="date",
            ),
        ]
        record = {
            "label": str(uuid.uuid4()),
            "description": "test item added to test correctness of api",
            "text": "test",
            "date": datetime.now().date(),
            "dateQualifier": datetime.now().year,
            "item_id": "Q377",
            "url": "https://example.org",
            "year": 2000,
            "identifier": str(uuid.uuid4()),
        }

        # test creating an item
        result = wd.add_record(
            record=record, property_mappings=property_mappings, write=True
        )
        self.check_add_result(result)

        actual = wd.get_record(result.qid, property_mappings=property_mappings)
        self.assertDictEqual(record, actual)

        # test modifying an item (not overwriting existing value)
        record["year"] = [record["year"], 2022]
        result = wd.add_record(
            {"year": 2022},
            property_mappings=property_mappings,
            item_id=result.qid,
            write=True,
        )
        self.check_add_result(result)
        actual = wd.get_record(result.qid, property_mappings=property_mappings)
        self.assertDictEqual(record, actual)

    @unittest.skipIf(
        BaseTest.inPublicCI(),
        "Tests creating and modifying items. To run in CI setup credentials",
    )
    def test_addDict(self):
        """
        test addDict
        """
        debug = self.debug
        debug = True
        wd = Wikidata(baseurl="https://test.wikidata.org", debug=debug)
        wd.loginWithCredentials()
        legacy_mappings = [
            {
                "Entity": "proceedings",
                "Column": None,
                "PropertyName": "instanceof",
                "PropertyId": "P95201",
                "Value": "Q377",
                "Type": "itemid",
                "Qualifier": None,
                "Lookup": None,
            },
            {
                "Entity": "proceedings",
                "Column": "short name",
                "PropertyName": "short name",
                "PropertyId": "P95227",
                "Type": "text",
                "Qualifier": None,
                "Lookup": "",
            },
            {
                "Entity": "proceedings",
                "Column": "pubDate",
                "PropertyName": "publication date",
                "PropertyId": "P95226",
                "Type": "date",
                "Qualifier": None,
                "Lookup": "",
            },
            {
                "Entity": "proceedings",
                "Column": "url",
                "PropertyName": "described at URL",
                "PropertyId": "P95231",
                "Type": "url",
                "Qualifier": None,
                "Lookup": "",
            },
            {
                "Entity": "proceedings",
                "Column": "language of work or name",
                "PropertyName": "language of work or name",
                "PropertyId": "P82",
                "Type": "itemid",
                "Qualifier": "url",
                "Lookup": "",
            },
            {
                "Entity": "proceedings",
                "Column": "urn",
                "PropertyName": "URN-NBN",
                "PropertyId": "P95232",
                "Type": "extid",
                "Qualifier": None,
                "Lookup": "",
            },
        ]
        mappings = [
            PropertyMapping(
                "instanceof",
                "instanceof",
                "P95201",
                propertyType=WdDatatype.itemid,
                value="Q1143604",
            ),
            PropertyMapping(
                "short name", "short name", "P95227", propertyType=WdDatatype.text
            ),
            PropertyMapping(
                "pubDate", "publication date", "P95226", propertyType=WdDatatype.date
            ),
            PropertyMapping(
                "url", "described at URL", "P95231", propertyType=WdDatatype.url
            ),
            PropertyMapping(
                "language of work or name",
                "language of work or name",
                "P82",
                propertyType=WdDatatype.itemid,
                qualifierOf="url",
            ),
            PropertyMapping("urn", "URN-NBN", "P95232", propertyType=WdDatatype.extid),
        ]
        record = {
            "label": str(uuid.uuid4()),
            "short name": "test",
            "pubDate": datetime.now().date(),
            "url": "http://example.org",
            "language of work or name": "Q377",
            "urn": str(uuid.uuid4()),
        }
        mapDict, _ = LOD.getLookup(legacy_mappings, "PropertyId")
        result = wd.addDict(record, mapDict=mapDict, write=True)
        self.check_add_result(result)
        actual = wd.get_record(result.qid, mappings)
        record["instanceof"] = "Q377"
        self.assertEqual(record, actual)

    @unittest.skipIf(
        BaseTest.inPublicCI(),
        "Tests creating and modifying items. To run in CI setup credentials",
    )
    def test_value_lookup(self):
        """
        tests the lookup of wikidata ids from label value
        Note: Currently the lookup is always against wikidata. Changing this requires to adapt this test accordingly.
        """
        lookup_type, label, expected_qid = (
            "Q3336843",  # constituent country of the United Kingdom - Wikidata
            "Scotland",  # label to lookup
            "Q22",  # expected lookup result
        )  # type qid, label, qid
        mappings = [
            PropertyMapping(
                column="country_id",
                propertyName="wikibase-item sandbox property",
                propertyId="P95201",
                propertyType=WdDatatype.itemid,
                valueLookupType=lookup_type,
            )
        ]
        # let't try adding a dict
        entity_label = f"str(uuid.uuid4())"
        record = {"label": entity_label, "country_id": label}
        expected_record = {"label": entity_label, "country_id": expected_qid}

        debug = self.debug
        # debug = True
        wd = Wikidata(baseurl="https://test.wikidata.org", debug=debug)
        wd.loginWithCredentials()
        result = wd.add_record(record, mappings, write=True)
        self.check_add_result(result)
        actual = wd.get_record(result.qid, mappings)
        self.assertDictEqual(expected_record, actual)

    @unittest.skipIf(BaseTest.inPublicCI(), "Tests creating statement with two values")
    def test_claim_with_two_values(self):
        """
        Tests adding a statement with two values by handing over a list
        """
        property_mappings = [
            WikidataSandboxProperties.TEXT,
            WikidataSandboxProperties.ITEM,
            WikidataSandboxProperties.DATE,
            WikidataSandboxProperties.URL,
            WikidataSandboxProperties.EXT_ID,
        ]
        record = {
            "label": str(uuid.uuid4()),
            "description": "test item added to test correctness of api",
            "text": ["Hello", "World"],
            "date": [
                datetime.now().date(),
                datetime.fromisoformat("2000-01-01").date(),
            ],
            "url": ["http://example.org", "http://example.org/test"],
            "item_id": ["Q377", "Q344"],
            "identifier": [str(uuid.uuid4()), str(uuid.uuid4())],
        }
        result = self.test_wikidata.add_record(
            record, property_mappings=property_mappings, write=True
        )
        self.check_add_result(result)
        actual_record = self.test_wikidata.get_record(
            result.qid, property_mappings=property_mappings
        )
        self.assertDictEqual(record, actual_record)

    def test_get_datatype_of_property(self):
        """
        tests get_datatype_of_property
        """
        test_params = [
            ("P31", "WikibaseItem"),
            ("31", "WikibaseItem"),
            (31, "WikibaseItem"),
            ("P580", "Time"),
            ("P1813", "Monolingualtext"),
            ("P856", "Url"),
            ("P8978", "ExternalId"),
        ]
        for param in test_params:
            with self.subTest(param=param):
                pid, expected = param
                actual = self.wd.get_datatype_of_property(pid)
                self.assertEqual(expected, actual)

    def test_get_wddatatype_of_property(self):
        """
        tests get_datatype_of_property
        """
        test_params = [
            ("P31", WdDatatype.itemid),
            ("31", WdDatatype.itemid),
            (31, WdDatatype.itemid),
            ("P580", WdDatatype.date),
            ("P1813", WdDatatype.text),
            ("P856", WdDatatype.url),
            ("P8978", WdDatatype.extid),
            ("P478", WdDatatype.string),
        ]
        for param in test_params:
            with self.subTest(param=param):
                pid, expected = param
                actual = self.wd.get_wddatatype_of_property(pid)
                self.assertEqual(expected, actual)

    def test_UrlReference(self):
        """
        tests UrlReference
        """
        test_params = [("http://example.org", "2022-01-01")]
        for param in test_params:
            with self.subTest(param=param):
                url, date = param
                reference = UrlReference(url, date)
                json = reference.get_json()
                json_str = str(json)
                self.assertIn("P854", json_str)
                self.assertIn("P813", json_str)
                self.assertIn(url, json_str)
                self.assertIn(date, json_str)

    @unittest.skipIf(BaseTest.inPublicCI(), "querying wikidata endpoint")
    def test_normalize_records(self):
        """
        tests normalize_records
        """
        prop_maps = [
            PropertyMapping(
                column="country",
                propertyType=WdDatatype.itemid,
                propertyName="country",
                propertyId="P17",
                valueLookupType="Q3624078",
            ),
            PropertyMapping(
                column="city",
                propertyType=WdDatatype.itemid,
                propertyName="location",
                propertyId="P276",
            ),
            PropertyMapping(
                column="location",
                propertyType=WdDatatype.itemid,
                propertyName="location",
                propertyId="P276",
            ),
            PropertyMapping(
                column="loc",
                propertyType=WdDatatype.itemid,
                propertyName="location",
                propertyId="P276",
            ),
            PropertyMapping(
                column=None,
                propertyType=WdDatatype.itemid,
                propertyName="location",
                propertyId="P276",
                value="Q5",
            ),
        ]
        record = {"country": "Germany", "city": "Q64", "location": None, "loc": ""}
        exp_normalized_record = {
            "country": WikidataItem("Q183", "Germany"),
            "city": WikidataItem("Q64", "Berlin"),
            "location": None,
            "loc": None,
        }
        actual_normalized_record = self.wd.normalize_records(record, prop_maps)
        self.assertDictEqual(exp_normalized_record, actual_normalized_record)

    @unittest.skipIf(BaseTest.inPublicCI(), "querying wikidata endpoint")
    def test_get_wikidata_item(self):
        """
        tests get_wikidata_item
        """
        test_params = [
            ("Germany", "Q3624078", WikidataItem("Q183", "Germany")),
            ("Q183", None, WikidataItem("Q183", "Germany")),
        ]
        for test_param in test_params:
            with self.subTest(test_param=test_param):
                qid_or_label, item_type_qid, expected = test_param
                actual = self.wd.get_wikidata_item(qid_or_label, item_type_qid)
                self.assertEqual(expected, actual)

    def test_convert_to_yaml(self):
        """
        test converting the PropertyMappings to YAML
        """
        sb_dict = {
            "text_field": WikidataSandboxProperties.TEXT,
            "date_field": WikidataSandboxProperties.DATE,
            "item_field": WikidataSandboxProperties.ITEM,
            "url_field": WikidataSandboxProperties.URL,
            "year_field": WikidataSandboxProperties.YEAR,
            "extid_field": WikidataSandboxProperties.EXT_ID,
        }
        pm = PropertyMappings(
            name="sandbox_props",
            description="TSandbox Properties for Testing",
            url="https://test.wikidata.org",
            mappings=sb_dict,
        )

        yaml_str = pm.to_yaml()
        if self.debug:
            print(yaml_str)


class WikidataSandboxProperties:
    """
    Wikidata sandbox items to be used to add and modify items in test.wikidata.org
    """

    TEXT = PropertyMapping(
        column="text",
        propertyId="P95227",
        propertyName="monolingualtext sandbox property",
        propertyType=WdDatatype.text,
    )
    DATE = PropertyMapping(
        column="date",
        propertyId="P95226",
        propertyName="time sandbox property",
        propertyType=WdDatatype.date,
    )
    ITEM = PropertyMapping(
        column="item_id",
        propertyId="P95201",
        propertyName="wikibase-item sandbox property",
        propertyType=WdDatatype.itemid,
    )
    URL = PropertyMapping(
        column="url",
        propertyId="P95231",
        propertyName="url sandbox property",
        propertyType=WdDatatype.url,
    )
    YEAR = PropertyMapping(
        column="year",
        propertyId="P96927",
        propertyName="year sandbox property",
        propertyType=WdDatatype.year,
    )
    EXT_ID = PropertyMapping(
        column="identifier",
        propertyId="P95232",
        propertyName="external-id sandbox property",
        propertyType=WdDatatype.extid,
    )
