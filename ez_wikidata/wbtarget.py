"""
Created on 2026-10-25

Wikibase targets other than Wikidata with per-target id translation
see https://github.com/WolfgangFahl/py_ez_wikidata/issues/20

@author: wf
"""

import os
import re
from dataclasses import field, replace
from typing import Any, Dict, List, Optional, Tuple

from basemkit.yamlable import lod_storable

from ez_wikidata.wdproperty import PropertyMapping


@lod_storable
class TargetId:
    """
    the id and label of an entity on a target Wikibase
    """

    id: str
    label: Optional[str] = None


@lod_storable
class IdTranslation:
    """
    translation table Wikidata id -> target id
    """

    name: str
    source: Optional[str] = None
    ids: Dict[str, TargetId] = field(default_factory=dict)


@lod_storable
class WikibaseTarget:
    """
    a Wikibase instance to write to
    """

    name: str
    baseurl: str
    sparql_endpoint: Optional[str] = None
    concept_uri: Optional[str] = None
    translate: bool = False

    def __post_init__(self):
        """
        initialize the not yet loaded translation table
        """
        self.translation = None

    @classmethod
    def resource_path(cls, *parts: str) -> str:
        """
        get the path of a bundled resource

        Args:
            parts: the path parts below the resources directory

        Returns:
            str: the path of the resource
        """
        path = os.path.join(os.path.dirname(__file__), "resources", *parts)
        return path

    @classmethod
    def of_name(cls, name: str) -> "WikibaseTarget":
        """
        get the bundled target of the given name with its translation table

        Args:
            name(str): the target name e.g. test or factgrid

        Raises:
            ValueError: if there is no target with the given name

        Returns:
            WikibaseTarget: the target
        """
        targets = WikibaseTargets.of_bundle()
        target = targets.targets.get(name)
        if target is None:
            names = ", ".join(targets.targets.keys())
            raise ValueError(f"unknown Wikibase target {name} - known: {names}")
        target.load_translation()
        return target

    @classmethod
    def of_baseurl(cls, baseurl: str) -> Optional["WikibaseTarget"]:
        """
        get the bundled target with the given baseurl

        Args:
            baseurl(str): the baseurl e.g. https://database.factgrid.de

        Returns:
            Optional[WikibaseTarget]: the target or None if there is none
        """
        target = None
        targets = WikibaseTargets.of_bundle()
        for candidate in targets.targets.values():
            if candidate.baseurl == baseurl.rstrip("/"):
                target = cls.of_name(candidate.name)
        return target

    def load_translation(self):
        """
        load my translation table if I translate
        """
        if self.translate and self.translation is None:
            path = self.resource_path("targets", f"{self.name}.yaml")
            self.translation = IdTranslation.load_from_yaml_file(path)

    def translate_id(self, wd_id: str) -> Optional[str]:
        """
        translate the given Wikidata id to my id

        Args:
            wd_id(str): the Wikidata property or item id e.g. P31

        Returns:
            Optional[str]: my id or None if I have no id for it
        """
        target_id = wd_id
        if self.translate:
            entry = self.translation.ids.get(wd_id)
            target_id = entry.id if entry else None
        return target_id

    def get_label(self, target_id: str) -> Optional[str]:
        """
        get the label of the given id of mine from the translation table

        Args:
            target_id(str): my property or item id

        Returns:
            Optional[str]: the label or None if not known
        """
        label = None
        if self.translation is not None:
            for entry in self.translation.ids.values():
                if entry.id == target_id:
                    label = entry.label
        return label

    def _translate_value(self, value: Any) -> Tuple[Any, List[str]]:
        """
        translate the Wikidata item ids in the given value

        Args:
            value: a single value or a list of values

        Returns:
            Tuple[Any, List[str]]: the translated value (None for an item id
            without translation) and the untranslated item ids
        """
        missing = []
        values = value if isinstance(value, list) else [value]
        translated = []
        for single in values:
            if isinstance(single, str) and re.fullmatch(r"Q\d+", single):
                target_id = self.translate_id(single)
                if target_id is None:
                    missing.append(single)
                single = target_id
            translated.append(single)
        result = translated if isinstance(value, list) else translated[0]
        if missing:
            result = None
        return result, missing

    def translate_mappings(
        self, property_mappings: List[PropertyMapping], record: dict
    ) -> Tuple[List[PropertyMapping], dict, List[str]]:
        """
        translate the given Wikidata based mappings and record to my ids;
        a mapping without translation is skipped with its record column and
        reported, never silently written with the Wikidata id

        Args:
            property_mappings(List[PropertyMapping]): the Wikidata based mappings
            record(dict): the record

        Returns:
            Tuple[List[PropertyMapping], dict, List[str]]: the translated
            mappings, the record with translated item values and the problems
        """
        problems = []
        translated = []
        record = dict(record)
        skipped_columns = set()
        if not self.translate:
            translated = list(property_mappings)
        else:
            for pm in property_mappings:
                skip_reason = None
                target_pm = pm
                if not pm.is_item_itself():
                    target_pid = self.translate_id(pm.propertyId)
                    value, missing_values = self._translate_value(pm.value)
                    record_value = record.get(pm.column) if pm.column else None
                    if record_value is not None:
                        record_value, missing_record = self._translate_value(
                            record_value
                        )
                        missing_values.extend(missing_record)
                    if target_pid is None:
                        skip_reason = f"no id for {pm.propertyId} ({pm.propertyName})"
                    elif pm.is_qualifier() and pm.qualifierOf in skipped_columns:
                        skip_reason = f"qualified column {pm.qualifierOf} is skipped"
                    elif missing_values:
                        skip_reason = f"no id for {', '.join(missing_values)}"
                    elif (
                        pm.valueLookupType
                        and isinstance(record_value, str)
                        and not re.fullmatch(r"Q\d+", record_value)
                    ):
                        skip_reason = "value lookup by label is Wikidata only"
                    else:
                        target_pm = replace(pm, propertyId=target_pid, value=value)
                        if pm.column and pm.column in record:
                            record[pm.column] = record_value
                if skip_reason is None:
                    translated.append(target_pm)
                else:
                    skipped_columns.add(pm.column)
                    record_value = record.pop(pm.column, None)
                    if record_value is not None or pm.value is not None:
                        problems.append(
                            f"{skip_reason} on {self.name} - {pm.column} is skipped"
                        )
        return translated, record, problems


@lod_storable
class WikibaseTargets:
    """
    the bundled Wikibase targets
    """

    targets: Dict[str, WikibaseTarget] = field(default_factory=dict)

    @classmethod
    def of_bundle(cls) -> "WikibaseTargets":
        """
        load the bundled targets from resources/wikibases.yaml

        Returns:
            WikibaseTargets: the targets
        """
        path = WikibaseTarget.resource_path("wikibases.yaml")
        targets = cls.load_from_yaml_file(path)
        return targets
