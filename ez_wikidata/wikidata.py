"""
Created on 2022-04-18

@author: wf
"""

import datetime
import json
import os
import re
import textwrap
import traceback
import typing
from dataclasses import dataclass, field
from itertools import groupby
from pathlib import Path
from typing import Dict, List, Optional, Union

import dateutil.parser
from lodstorage.prefixes import Prefixes
from lodstorage.sparql import SPARQL
from wikibaseintegrator import WikibaseIntegrator, wbi_login
from wikibaseintegrator.datatypes import (
    URL,
    BaseDataType,
    ExternalID,
    Item,
    MonolingualText,
    String,
    Time,
)
from wikibaseintegrator.entities import ItemEntity
from wikibaseintegrator.models import Claim, Reference, Snak
from wikibaseintegrator.wbi_config import config as wbi_config
from wikibaseintegrator.wbi_enums import WikibaseRank, WikibaseTimePrecision

from ez_wikidata.version import Version
from ez_wikidata.wdproperty import (
    PropertyMapping,
    PropertyMappings,
    Variable,
    WdDatatype,
    WikidataPropertyManager,
)


@dataclass
class WikidataResult:
    """
    a class for handling a wikidata result
    """

    item: Optional[ItemEntity] = None
    errors: Dict[str, Exception] = field(default_factory=dict)
    qid: Optional[str] = None
    msg: Optional[str] = None
    debug: Optional[bool] = False

    def __post_init__(self):
        # If qid is not provided, derive it from item
        if self.qid is None and self.item:
            self.qid = self.item.id

    @property
    def pretty_item_json(self, indent: int = 2) -> str:
        """Returns a pretty-printed JSON string of the item."""
        if self.item:
            item_dict = (
                self.item.get_json()
            )  # Assuming get_json() returns a JSON string representation of the item
            pretty_json = json.dumps(item_dict, indent=indent)
        else:
            pretty_json = self.qid
        return pretty_json


class Wikidata:
    """
    wikidata access

    see http://learningwikibase.com/data-import/
    """

    TEST_WD_URL = "https://test.wikidata.org"
    WD_URL = "https://www.wikidata.org"

    def __init__(
        self,
        baseurl: str = None,
        wpm: WikidataPropertyManager = None,
        debug: bool = False,
    ):
        """
        Constructor

        Args:
            baseurl(str): the baseurl of the wikibase to use
            debug(bool): if True output debug information
            wpm(WikidataPropertymanager):
        """
        if baseurl is None:
            baseurl = self.WD_URL
        self.baseurl = baseurl
        self.debug = debug
        self.apiurl = f"{self.baseurl}/w/api.php"
        self.login = None
        self.user = None
        self._wbi = None
        if wpm is None:
            wpm = WikidataPropertyManager.get_instance()
        self.wpm = wpm

    @property
    def wbi(self) -> WikibaseIntegrator:
        """
        WikibaseIntegrator
        """
        if self._wbi is None or (self.login is not None and self._wbi.login is None):
            wbi_config["USER_AGENT"] = (
                f"{Version.name}/{Version.version} (https://www.wikidata.org/wiki/User:{self.user})"
            )
            wbi_config["MEDIAWIKI_API_URL"] = self.apiurl
            self._wbi = WikibaseIntegrator(login=self.login)
        return self._wbi

    @wbi.setter
    def wbi(self, wbi: typing.Union[WikibaseIntegrator, None]):
        """
        set the WikibaseIntegrator
        """
        self._wbi = wbi

    def getCredentials(self) -> (str, str):
        """
        get my credentials https://test.wikidata.org/wiki/Property:P370

        from the wd npm command line tool

        Throws:
            Exception: if no credentials are available for the baseurl

        Returns:
            (username, password) of the account assigned to the baseurl
        """
        user = None
        pwd = None
        home = str(Path.home())
        configFilePath = f"{home}/.config/wikibase-cli/config.json"
        if os.path.isfile(configFilePath):
            with open(configFilePath, mode="r") as f:
                wikibaseConfigJson = json.load(f)
                credentials = wikibaseConfigJson["credentials"]
                credentialRecord = credentials.get(self.baseurl, None)
                if (
                    self.baseurl == self.TEST_WD_URL
                    and self.baseurl not in credentials
                    and self.WD_URL in credentials
                ):
                    credentialRecord = credentials.get(self.WD_URL)
                if credentialRecord is None:
                    raise Exception(f"no credentials available for {self.baseurl}")
                user = credentialRecord["username"]
                pwd = credentialRecord["password"]
        return user, pwd

    def loginWithCredentials(self, user: str = None, pwd: str = None):
        """
        login using the given credentials or credentials
        retrieved via self.getCredentials

        Args:
            user(str): the username
            pwd(str): the password
        """
        if user is None:
            user, pwd = self.getCredentials()

        if user is not None:
            self.login = wbi_login.Login(
                user=user, password=pwd, mediawiki_api_url=self.apiurl
            )
            if self.login:
                self.user = user

    def logout(self):
        """
        log the user out again
        """
        self.user = None
        self.login = None
        self.wbi = None

    def getItemByName(
        self, itemName: str, itemType: str, lang: str = "en"
    ) -> typing.Optional[str]:
        """
        get an item by Name
        ToDo: Needs to be reworked as always WDQS is used as endpoint even if a different one is defined
        Args:
            itemName(str): the item to look for
            itemType(str): the type of the item
            lang(str): the language of the itemName
        """
        itemLabel = f'"{itemName}"@{lang}'
        sparqlQuery = """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX wdt: <http://www.wikidata.org/prop/direct/>
            PREFIX wd: <http://www.wikidata.org/entity/>

            SELECT ?item ?itemLabel
            WHERE {
              {
                ?item wdt:P31|wdt:P31/wdt:P279 wd:%s.
                ?item rdfs:label ?itemLabel.
                # short name
                BIND(%s as ?shortNameLabel )
                ?item wdt:P1813 ?shortNameLabel
                FILTER(LANG(?itemLabel)= "%s" )
              } UNION {
                ?item wdt:P31|wdt:P31/wdt:P279 wd:%s.
                BIND(%s as ?itemLabel )
                ?item rdfs:label ?itemLabel.
              }
            }""" % (
            itemType,
            itemLabel,
            lang,
            itemType,
            itemLabel,
        )
        endpointUrl = "https://query.wikidata.org/sparql"
        sparql = SPARQL(endpointUrl)
        itemRows = sparql.queryAsListOfDicts(sparqlQuery)
        item = None
        if len(itemRows) > 0:
            item = itemRows[0]["item"].replace("http://www.wikidata.org/entity/", "")
        return item

    def addDict(
        self,
        row: dict,
        mapDict: dict,
        itemId: Union[str, None] = None,
        lang: str = "en",
        write: bool = False,
        ignoreErrors: bool = False,
    ) -> WikidataResult:
        """
        add the given row mapping with the given map Dict

        Args:
            row(dict): the data row to add
            mapDict(dict): the mapping dictionary to use
            itemId: wikidata id of the item the data should be added to. If None a new item is created unless item id is provided in the record
            lang(str): the language for lookups
            write(bool): if True do actually write
            ignoreErrors(bool): if True ignore errors

        Returns:
            WikiDataResult: the result of the operation
        """
        mappings = self.wpm.get_mappings_for_records(mapDict)
        return self.add_record(
            row,
            mappings,
            item_id=itemId,
            lang=lang,
            write=write,
            ignore_errors=ignoreErrors,
        )

    def get_record(
        self,
        item_id: str,
        property_mappings: Union[
            List[str], List["PropertyMapping"], typing.Dict[str, dict]
        ],
        include_label: bool = True,
        include_description: bool = True,
        label_for_qids: bool = False,
    ) -> dict:
        """
        Get the properties form the given item
        Args:
            item_id: id of the item to get the data from
            property_mappings: list of property values to extract
            include_label:
            include_description:
            label_for_qids: If True fetch the label for a linked Qid
        Returns:
            dict with the property values
        """
        item = self.wbi.item.get(item_id)
        lang = "en"
        if isinstance(property_mappings, dict):
            property_mappings = PropertyMappings.from_dict(property_mappings)  # @UndefinedVariable
        record = dict()
        if include_label and item.labels.get(lang) is not None:
            record["label"] = item.labels.get(lang).value
        if include_description and item.descriptions.get(lang) is not None:
            record["description"] = item.descriptions.get(lang).value
        qualifier_lookup = PropertyMapping.get_qualifier_lookup(property_mappings)
        pms = []
        for pm in property_mappings:
            if not isinstance(pm, PropertyMapping) or not pm.is_qualifier():
                pms.append(pm)
        for prop in pms:
            prop_id = prop
            if isinstance(prop, PropertyMapping):
                prop_id = prop.propertyId
            statements = self._get_statements_by_pid(item, prop_id)
            prop_label = prop_id
            if isinstance(prop, PropertyMapping):
                prop_label = prop.column
            values = []
            for statement in statements:
                value = self._get_statement_value(statement)
                if label_for_qids:
                    if (
                        prop.valueLookupType is not None
                        and statement.mainsnak.datatype == "wikibase-item"
                    ):
                        label = self.get_item_label(value, lang)
                        if label is not None:
                            value = label
                values.append(value)
                if (
                    isinstance(prop, PropertyMapping)
                    and prop.column in qualifier_lookup
                ):
                    for qualifier_pm in qualifier_lookup[prop.column]:
                        if qualifier_pm.propertyId in statement.qualifiers.qualifiers:
                            qualifier_statements = statement.qualifiers.get(
                                qualifier_pm.propertyId
                            )
                        else:
                            qualifier_statements = []
                        qualifier_values = []
                        for qualifier_statement in qualifier_statements:
                            qualifier_values.append(
                                self._get_statement_value(qualifier_statement)
                            )
                        record[qualifier_pm.column] = (
                            qualifier_values[0]
                            if len(qualifier_values) == 1
                            else qualifier_values
                        )
            if len(values) == 1:
                record[prop_label] = values[0]
            elif values == []:
                record[prop_label] = None
            else:
                record[prop_label] = values
        return record

    def get_item_label(self, item_id: str, lang: str = None) -> typing.Union[str, None]:
        """
        Get the label for the given item id
        Args:
            item_id: id of the item
            lang: label language to return. Default is "en"

        Returns:
            str: label of the item
            None: If the label can not be determined or the item_id is None or can not be found
        """
        if lang is None:
            lang = "en"
        label = None
        if item_id is not None:
            linked_item = self.wbi.item.get(item_id)
            linked_item_label = linked_item.labels.get(lang)
            if linked_item_label is not None:
                label = linked_item_label.value
        return label

    def _get_statements_by_pid(self, item: ItemEntity, pid: str) -> List[Item]:
        """
        Get the property statements of the item for the given Pid.
        if ranking is established between the statements return only the highest rank
        Args:
            item: item to get the statements from
            pid: property id
        Returns:
            list: list of the property statements
        """
        if pid in item.claims:
            statements = item.claims.get(pid)
        else:
            statements = []
        if len(statements) > 1:
            ordered_stats = {
                k: list(g) for k, g in groupby(statements, lambda x: x.rank)
            }
            rank_by_preference = [
                WikibaseRank.PREFERRED,
                WikibaseRank.NORMAL,
                WikibaseRank.DEPRECATED,
            ]
            for rank in rank_by_preference:
                if rank in ordered_stats:
                    statements = ordered_stats[rank]
                    break
        return statements

    def _get_statement_value(self, statement: Union[Claim, Snak]) -> typing.Any:
        """
        Get the raw value of the statement without the metadata
        Args:
            statement: statement to extract the value from

        Returns:
            raw value of the statement
        """
        value = None
        snak = statement
        if isinstance(statement, Claim):
            snak = statement.mainsnak
        raw_value = snak.datavalue.get("value")
        datatype = snak.datatype
        if datatype == "wikibase-item":
            value = raw_value.get("id", None)
        elif datatype == "monolingualtext":
            value = raw_value.get("text")
        elif datatype == "string":
            value = raw_value
        elif datatype == "url":
            value = raw_value
        elif datatype == "time":
            value = dateutil.parser.parse(raw_value.get("time")[1:])
            precision = raw_value.get("precision")
            if precision == 11:
                value = value.date()
            elif precision == 9:
                value = value.year
        elif datatype == "external-id":
            value = raw_value
        else:
            pass
        return value

    def add_record(
        self,
        record: dict,
        property_mappings: List["PropertyMapping"],
        item_id: Union[str, None] = None,
        lang: str = "en",
        write: bool = False,
        ignore_errors: bool = False,
        summary: str = None,
        reference: Reference = None,
    ) -> WikidataResult:
        """
        add the given row mapping with the given map Dict

        Args:
            record(dict): the data row to add
            property_mappings(list): the mapping dictionary to use
            item_id: wikidata id of the item the data should be added to. If None a new item is created unless item id is provided in the record
            lang(str): the language for lookups
            write(bool): if True do actually write
            ignore_errors(bool): if True ignore errors
            summary: summary of the item edits
            reference: reference to add to all claims

        Returns:
            (qId, errors): the wikidata item create (if any) and a dict of errors
        """
        claims = []
        errors = dict()
        qualifier_lookup = PropertyMapping.get_qualifier_lookup(property_mappings)
        # check if there is a existing Q-Item identifier in the record
        item_mapping = PropertyMapping.get_item_mapping(property_mappings)
        if item_mapping is not None:
            if item_id is None:
                item_id = record.get(item_mapping.column, None)
        # get the relevant properties
        properties = []
        for pm in property_mappings:
            if not pm.is_qualifier() and not pm.is_item_itself():
                properties.append(pm)
            else:
                # breakpoint to debug ignored properties
                pass

        for prop in properties:
            qualifier_mappings = qualifier_lookup.get(prop.column, None)
            prop_claims, claim_errors = self._get_statement_for_property(
                record, prop, qualifier_mappings, reference, lang
            )
            # merge error dicts to one dict
            errors = {**errors, **claim_errors}
            claims.extend(prop_claims)
        label = self.sanitize_label(record.get("label", None))
        description = record.get("description", None)
        # handle get or create case
        item = self.get_or_create_item(item_id)
        item.add_claims(claims)
        if label:
            item.labels.set(language=lang, value=label)
        if description:
            item.descriptions.set(language=lang, value=description)
        if write:
            if len(errors) == 0 or ignore_errors:
                try:
                    item = item.write(summary=summary)
                except Exception as ex:
                    errors["write failed"] = ex
        result = WikidataResult(item=item, errors=errors, debug=self.debug)
        return result

    def _get_statement_for_property(
        self,
        record: dict,
        prop_mapping: "PropertyMapping",
        qualifier_mappings: Union[List["PropertyMapping"], None],
        reference: Reference,
        lang: str,
    ) -> (List[Claim], dict):
        """
        Get the claims that can be derived from the given property mapping and record.
        Generates a statement with its qualifiers and reference from the given record and mapping.
        If the record value of the property is a list multiple claims are generated

        Args:
            record: data record
            prop_mapping: property definition for the claims that should be generated from the given record
            qualifier_mappings: descriptions of the qualifiers of the property
            reference: reference of the statement
            lang: language to use

        Returns:
            list of statements
        """
        claims = []
        value = self.get_prop_value(record, prop_mapping, lang)
        values = value if isinstance(value, list) else [value]
        errors = dict()
        for value in values:
            statement = None
            try:
                statement = self.convert_to_claim(value=value, pm=prop_mapping)
            except Exception as ex:
                errors[prop_mapping.column] = ex
                if self.debug:
                    print(traceback.format_exc())
            if statement is not None:
                # add reference
                if reference is not None:
                    statement.references.add(reference)
                # add qualifier
                if qualifier_mappings is not None:
                    qualifier_errors = self._add_qualifier_to_statement(
                        record, statement, qualifier_mappings, lang
                    )
                    # merge error dicts to one dict
                    errors = {**errors, **qualifier_errors}
            if statement is not None:
                claims.append(statement)
        return claims, errors

    def _add_qualifier_to_statement(
        self,
        record: dict,
        statement: Claim,
        qualifier_mappings: List["PropertyMapping"],
        lang: str,
    ) -> dict:
        """
        add the qualifiers to the given statement
        Args:
            record:
            statement: add qualifiers to this statement
            qualifier_mappings: list of PropertyMappings of the qualifiers

        Returns:
            dict of occurred errors with the qualifier column as key. If no error occurs an empty dict is returned
        """
        errors = dict()
        for qualifier_pm in qualifier_mappings:
            qualifier_value = self.get_prop_value(record, qualifier_pm, lang)
            if qualifier_value is None:
                continue
            else:
                try:
                    qualifier = self.convert_to_claim(qualifier_value, qualifier_pm)
                    statement.qualifiers.add(qualifier)
                except Exception as ex:
                    errors[qualifier_pm.column] = ex
                    if self.debug:
                        print(traceback.format_exc())
        return errors

    def get_or_create_item(self, item_id: typing.Union[str, None]) -> ItemEntity:
        """
        Get or create the requested wikidata item
        Args:
            item_id: item to retrieve if None create a new item
        """
        if item_id is None or isinstance(item_id, str) and item_id.strip() == "":
            item = self.wbi.item.new()
        else:
            item = self.wbi.item.get(item_id)
        return item

    def get_prop_value(
        self, record: dict, pm: "PropertyMapping", lang: str
    ) -> typing.Any:
        """
        Retrieve the property value from the record and prepare the value if necessary
        Args:
            record: record containing the property data
            pm: property mapping
            lang: language to use

        Returns:
            value of the property from the record
        """
        value = record.get(pm.column, None)
        if value is None:
            value = pm.value
        if value and pm.valueLookupType and not self.is_wikidata_item_id(value):
            # find the wikidata item id of value
            value = self.getItemByName(value, pm.valueLookupType, lang)
        if value and isinstance(value, str):
            value = value.strip()
        return value

    def convert_to_claim(
        self, value, pm: "PropertyMapping"
    ) -> Union[BaseDataType, None]:
        """
        Convert the given value to a corresponding wikidata statement
        Args:
            value: value of the statement
            pm: information about the property statement ot generate

        Raises:
            Exception: if property datatype is unknown or not supported

        Returns:
            BaseDataType
        """
        if value is None or value == "":
            return None
        if pm.property_type_enum is None:
            pm.property_type_enum = self.get_wddatatype_of_property(pm.propertyId)
        if pm.property_type_enum is WdDatatype.year:
            yearString = f"+{value}-01-01T00:00:00Z"
            statement = Time(
                yearString, prop_nr=pm.propertyId, precision=WikibaseTimePrecision.YEAR
            )
        elif pm.property_type_enum is WdDatatype.date:
            statement = self.get_date_claim(value, pm.propertyId)
        elif pm.property_type_enum is WdDatatype.extid:
            statement = ExternalID(value=value, prop_nr=pm.propertyId)
        elif pm.property_type_enum is WdDatatype.string:
            statement = String(value=str(value), prop_nr=pm.propertyId)
        elif pm.property_type_enum is WdDatatype.text:
            statement = MonolingualText(text=str(value), prop_nr=pm.propertyId)
        elif pm.property_type_enum is WdDatatype.url:
            statement = URL(value=value, prop_nr=pm.propertyId)
        elif pm.property_type_enum is WdDatatype.itemid:
            statement = Item(value=value, prop_nr=pm.propertyId)
        else:
            raise Exception(
                f"({pm.property_type_enum}) unknown or not supported datatype"
            )
        return statement

    @staticmethod
    def get_date_claim(
        date: Union[str, datetime.date, datetime.datetime], prop_nr: Union[str, int]
    ) -> Claim:
        """
        Get the data statement for the given date and property id
        Args:
            date: date value
            prop_nr: id of the property

        Returns:
            statement of the given property number with the given value
        """
        if isinstance(date, datetime.date):
            date_value = datetime.datetime.combine(date, datetime.time())
        elif isinstance(date, datetime.datetime):
            date_value = date
        elif isinstance(date, str):
            date_value = dateutil.parser.parse(date)
        else:
            raise Exception(f"Value '{date}' can not be parsed to date")
        iso_date = date_value.isoformat()
        date_string = f"+{iso_date}Z"
        statement = Time(
            date_string, prop_nr=prop_nr, precision=WikibaseTimePrecision.DAY
        )
        return statement

    @staticmethod
    def is_wikidata_item_id(value: str) -> bool:
        """
        Returns true if the given value is a wikidata item id
        """
        return bool(re.fullmatch(r"Q[0-9]+", value))

    @staticmethod
    def is_wikidata_property_id(value: str) -> bool:
        """
        Returns true if the given value is a wikidata property id
        """
        return bool(re.fullmatch(r"P[0-9]+", value))

    @staticmethod
    def sanitize_label(label: str, limit: int = None, postfix: str = None) -> str:
        """
        sanitize given label by ensuring it is not too long
        Args:
            label: label to sanitize
            limit: max length of the label

        Returns:
            sanitized label
        """
        if limit is None:
            limit = 250
        if postfix is None:
            postfix = "..."
        if label is not None and len(label) > limit:
            label = label[: limit - len(postfix)] + postfix
        return label

    @classmethod
    def get_datatype_of_property(cls, property_id: Union[str, int]) -> Union[str, None]:
        """
        Get the datatype of the given property
        Args:
            property_id: id of the property e.g. P31 or 31

        Returns:
            datatype of the property of None if no datatype is defined
        """
        if isinstance(property_id, int) or not property_id.startswith("P"):
            property_id = f"P{property_id}"
        query = """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX wdt: <http://www.wikidata.org/prop/direct/>
            PREFIX wd: <http://www.wikidata.org/entity/>
            PREFIX wikibase: <http://wikiba.se/ontology#>

            SELECT Distinct ?o
            WHERE {
              wd:%s wikibase:propertyType ?o.
            }
        """ % (
            property_id
        )
        endpointUrl = "https://query.wikidata.org/sparql"
        sparql = SPARQL(endpointUrl)
        itemRows = sparql.queryAsListOfDicts(query)
        wikibase_prefix = "http://wikiba.se/ontology#"
        types = []
        for record in itemRows:
            types.append(record.get("o")[len(wikibase_prefix) :])
        if len(types) > 1:
            print("Property has more than one type! please check")
        elif len(types) == 0:
            print("Property has no defined datatype! please check")
            return None
        return types[0]

    @classmethod
    def get_wddatatype_of_property(cls, property_id: Union[str, int]) -> "WdDatatype":
        """
        Get the datatype of the given property
        Args:
            property_id: id of the property e.g. P31 or 31

        Returns:
            WdDatatype of the property of None if no datatype is defined
        """
        property_type = cls.get_datatype_of_property(property_id)
        return WdDatatype.get_by_wikibase(property_type)

    def normalize_records(self, record: dict, prop_map: typing.List["PropertyMapping"]):
        """
        Normalize given record by converting Qids to WikidataItem objects (lookup label) and find out Qid if label given
        based on the given prop_map
        """
        itemid_props = [
            p for p in prop_map if p.property_type_enum is WdDatatype.itemid
        ]
        for p in itemid_props:
            if p.column is None or p.column == "":
                continue
            value = record.get(p.column, None)
            if value is None and p.value is not None:
                value = p.value
            if isinstance(value, list):
                wd_item = [self.get_wikidata_item(v, p.valueLookupType) for v in value]
            else:
                wd_item = self.get_wikidata_item(value, p.valueLookupType)
            record[p.column] = wd_item
        return record

    def get_wikidata_item(
        self, qid_or_label: str, item_type_qid: str = None
    ) -> typing.Optional["WikidataItem"]:
        """
        Get WikidataItem for given label or Qid

        Args:
            qid_or_label: label or Qid of a item

        Returns:
            WikidataItem
        """
        item = None
        if qid_or_label is not None:
            if self.is_wikidata_item_id(qid_or_label):
                # lookup label
                qid = qid_or_label
                label = self.get_item_label(qid)
            else:
                # lookup label
                label = qid_or_label
                qid = self.getItemByName(label, item_type_qid)
            if qid is not None:
                item = WikidataItem(qid, label)
        return item


@dataclass
class WikidataItem:
    qid: str
    label: str
    lang: str = "en"
    sparql: Optional[SPARQL] = None
    debug: bool = False
    label: str = field(init=False, default=None)
    description: str = field(init=False, default=None)
    url: str = field(init=False)

    def __eq__(self, other) -> bool:
        """
        WikidataItems are equal if the qid is equal
        """
        same = isinstance(other, WikidataItem) and self.qid == getattr(
            other, "qid", None
        )
        return same

    def __post_init__(self):
        """
        handle the construction
        """
        if not self.qid:
            self.qid = None
            return
        self.url = f"https://www.wikidata.org/wiki/{self.qid}"
        # numeric qid
        self.qnumber = int(self.qid[1:])
        self.url = f"https://www.wikidata.org/wiki/{self.qid}"
        if self.sparql is not None:
            self.qlabel, self.description = WikidataItem.getLabelAndDescription(
                self.sparql, self.qid, self.lang, debug=self.debug
            )
            self.varname = Variable.validVarName(self.qlabel)
            self.itemVarname = f"{self.varname}Item"
            self.labelVarname = f"{self.varname}"

    def __str__(self):
        return self.asText(long=False)

    def asText(self, long: bool = True, wrapAt: int = 0):
        """
        returns my content as a text representation

        Args:
            long(bool): True if a long format including url is wished
            wrapAt(int): wrap long lines at the given width (if >0)

        Returns:
            str: a text representation of my content
        """
        text = self.qid or "❓"
        if hasattr(self, "qlabel"):
            text = f"{self.qlabel} ({self.qid})"
        if hasattr(self, "description"):
            desc = self.description
            if wrapAt > 0:
                desc = textwrap.fill(desc, width=wrapAt)
            text += f"☞{desc}"
        if long and hasattr(self, "url"):
            text += f"→ {self.url}"
        return text

    @classmethod
    def getLabelAndDescription(
        cls, sparql: SPARQL, itemId: str, lang: str = "en", debug: bool = False
    ):
        """
        get  the label for the given item and language

        Args:
            itemId(str): the wikidata Q/P id
            lang(str): the language of the label
            debug(bool): if True output debug information

        Returns:
            (str,str): the label and description as a tuple
        """
        query = f"""# get the label for the given item
{Prefixes.getPrefixes(["rdfs","wd","schema"])}
SELECT ?itemLabel ?itemDescription
WHERE
{{
  VALUES ?item {{
    wd:{itemId}
  }}
  ?item rdfs:label ?itemLabel.
  FILTER (LANG(?itemLabel) = "{lang}").
  ?item schema:description ?itemDescription.
  FILTER(LANG(?itemDescription) = "{lang}")
}}"""
        try:
            if debug:
                msg = f"getLabelAndDescription for wikidata Item {itemId} with query:\n{query}"
                print(msg)
            labelAndDescription = sparql.getValues(
                query, ["itemLabel", "itemDescription"]
            )
        except Exception as ex:
            msg = f"getLabelAndDescription failed for wikidata Item {itemId}:{str(ex)}"
            if debug:
                print(msg)
            raise Exception(msg)
        return labelAndDescription

    @classmethod
    def getItemsByLabel(
        cls, sparql: SPARQL, itemLabel: str, lang: str = "en", debug: bool = False
    ) -> list:
        """
        get a Wikidata items by the given label

        Args:
            sparql(SPARQL): the SPARQL endpoint to use
            itemLabel(str): the label of the items
            lang(str): the language of the label
            debug(bool): if True show debugging information

        Returns:
            a list of potential items
        """
        valuesClause = f'   "{itemLabel}"@{lang}\n'
        query = f"""# get the items that have the given label in the given language
# e.g. we'll find human=Q5 as the oldest type for the label "human" first
# and then the newer ones such as "race in Warcraft"
{Prefixes.getPrefixes(["rdfs","schema","xsd"])}
SELECT
  #?itemId
  ?item
  ?itemLabel
  ?itemDescription
WHERE {{
  VALUES ?itemLabel {{
    {valuesClause}
  }}
  #BIND (xsd:integer(SUBSTR(STR(?item),33)) AS ?itemId)
  ?item rdfs:label ?itemLabel.
  ?item schema:description ?itemDescription.
  FILTER(LANG(?itemDescription)="{lang}")
}}
#ORDER BY ?itemId"""
        qLod = sparql.queryAsListOfDicts(query)
        items = []
        for record in qLod:
            url = record["item"]
            qid = re.sub(r"http://www.wikidata.org/entity/(.*)", r"\1", url)
            item = WikidataItem(qid, debug=debug)
            item.url = url
            item.qlabel = record["itemLabel"]
            item.varname = Variable.validVarName(item.qlabel)
            item.description = record["itemDescription"]
            items.append(item)
        sortedItems = sorted(items, key=lambda item: item.qnumber)
        return sortedItems


class UrlReference(Reference):
    """
    Reference consisting of
        reference URL (P854)
        retrieved (P813)
    """

    def __init__(
        self, url, date: Union[str, datetime.date, datetime.datetime, None] = None
    ):
        """
        constructor
        Args:
            url: reference URL
            date: retrieved at
        """
        super().__init__()
        self.url = url
        if date is None:
            date = datetime.date.today()
        self.date = date
        self.add(URL(value=self.url, prop_nr="P854"))
        self.add(Wikidata.get_date_claim(date, prop_nr="P813"))
