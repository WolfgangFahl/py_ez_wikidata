"""
Created on 2026-06-26

@author: wf
"""

import io
import os
import tempfile
from contextlib import redirect_stdout

import yaml

from ez_wikidata.ezwd_cmd import EzWdCmd, main
from tests.basetest import BaseTest


class TestEzWdCmd(BaseTest):
    """
    test the ezwd command line interface
    """

    def setUp(self, debug=True, profile=True):
        BaseTest.setUp(self, debug=debug, profile=profile)

    def run_cmd(self, argv) -> str:
        """
        run the ezwd command with the given argv and capture stdout
        """
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = main(argv)
        self.assertEqual(0, exit_code)
        return buf.getvalue()

    def test_list_mappings(self):
        """
        test listing the columns of the bundled scholar mapping (offline)
        """
        out = self.run_cmd(["--mapping", "scholar", "--list-mappings"])
        self.assertIn("scholar_props", out)
        # a few documented Scholar properties must be present
        for token in ["P31", "P496", "P2456", "P12861", "entity_schema"]:
            self.assertIn(token, out)

    def test_help_no_args(self):
        """
        test that invoking ezwd without an action prints usage (offline)
        """
        out = self.run_cmd([])
        self.assertIn("usage:", out)
        self.assertIn("--mapping", out)

    def test_dry_run(self):
        """
        test that a dry-run run of the command shows the item that would be
        written
        """
        record = {
            "label": "Test Person",
            "description": "test",
            "instanceof": "Q5",
            "occupation": "Q1650915",
            "researchGate": "Test-Person",
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            record_path = os.path.join(tmp_dir, "test_person.yaml")
            with open(record_path, "w") as record_file:
                yaml.safe_dump(record, record_file)
            # run without -w will start dry-run
            out = self.run_cmd(["--mapping", "scholar", "--record", record_path])
        if self.debug:
            print(out)
        for token in ["Test Person", "P31", "Q5", "P106", "Q1650915", "P2038"]:
            self.assertIn(token, out)

    def test_paper_dry_run(self):
        """
        test that a dry-run of the paper mapping shows the statements of
        Q141609355 GraphWiseLearn - see issue #14
        """
        record = {
            "label": "GraphWiseLearn: Personalized Learning Through Semantified TEL, Leveraging QA-Enhanced LLM-Generated Content",
            "description": "scholarly article published in 2025",
            "title": "GraphWiseLearn: Personalized Learning Through Semantified TEL, Leveraging QA-Enhanced LLM-Generated Content",
            "author": "Q110462723",
            "language": "Q1860",
            "publication_date": "2025-01-28",
            "pages": "74-83",
            "doi": "10.1007/978-3-031-78955-7_8",
            "dblp": "conf/esws/Fahl24",
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            record_path = os.path.join(tmp_dir, "graphwiselearn.yaml")
            with open(record_path, "w") as record_file:
                yaml.safe_dump(record, record_file)
            out = self.run_cmd(
                ["--mapping", "paper", "--record", record_path, "--strict"]
            )
        if self.debug:
            print(out)
        for token in [
            "Q13442814",
            "P1476",
            "Q110462723",
            "P407",
            "+2025-01-28T00:00:00Z",
            "74-83",
            "10.1007/978-3-031-78955-7_8",
            "conf/esws/Fahl24",
            "P1545 series ordinal: 1",
        ]:
            self.assertIn(token, out)

    def write_record(self, tmp_dir: str, name: str, record: dict) -> str:
        """
        write the given record as YAML file into the given directory
        """
        record_path = os.path.join(tmp_dir, f"{name}.yaml")
        with open(record_path, "w") as record_file:
            yaml.safe_dump(record, record_file)
        return record_path

    def test_paper_authors_dry_run(self):
        """
        test that the authors of a paper get their 1-based list index as
        series ordinal - Q111500468 Persistent Identification for Conferences,
        see issue #15
        """
        authors = [
            "Q115164606",
            "Q55685947",
            "Q56448921",
            "Q110462723",
            "Q57169981",
            "Q30276490",
        ]
        record = {
            "label": "Persistent Identification for Conferences",
            "description": "scholarly article",
            "title": "Persistent Identification for Conferences",
            "author": authors,
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            record_path = self.write_record(tmp_dir, "q111500468", record)
            out = self.run_cmd(
                ["--mapping", "paper", "--record", record_path, "--strict"]
            )
        if self.debug:
            print(out)
        expected = []
        for index, author in enumerate(authors):
            expected.append(f"  P50 author: {author}")
            expected.append(f"    P1545 series ordinal: {index + 1}")
        lines = [line for line in out.splitlines() if "P50" in line or "P1545" in line]
        self.assertEqual(expected, lines)

    def test_example(self):
        """
        test that --example prints the embedded record of the paper mapping and
        its dry run - see issue #19
        """
        out = self.run_cmd(["--mapping", "paper", "--example", "--strict"])
        if self.debug:
            print(out)
        for token in [
            "https://www.wikidata.org/wiki/Q141609355",
            "doi: 10.1007/978-3-031-78955-7_8",
            "# dry-run:",
            "P50 author: Q110462723",
            "P1545 series ordinal: 1",
        ]:
            self.assertIn(token, out)

    def test_format_turtle(self):
        """
        test that --format turtle prints the built item in the Wikidata RDF
        model with the author order as pq:P1545 - see issue #8
        """
        record = {
            "label": "Persistent Identification for Conferences",
            "title": "Persistent Identification for Conferences",
            "author": ["Q115164606", "Q55685947", "Q56448921"],
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            record_path = self.write_record(tmp_dir, "q111500468", record)
            out = self.run_cmd(
                ["--mapping", "paper", "--record", record_path, "--format", "turtle"]
            )
        if self.debug:
            print(out)
        self.assertEqual(3, out.count("ps:P50 wd:Q"))
        for ordinal in ["1", "2", "3"]:
            self.assertIn(f'pq:P1545 "{ordinal}"', out)
        self.assertIn("@prefix wdt:", out)

    def test_strict_unmapped_column(self):
        """
        test that --strict refuses a record column without mapping, e.g.
        ordinals supplied for authors - see issues #13 and #15
        """
        record = {
            "label": "Persistent Identification for Conferences",
            "author": ["Q115164606", "Q55685947"],
            "series_ordinal": ["1", "1"],
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            record_path = self.write_record(tmp_dir, "unmapped", record)
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = main(
                    ["--mapping", "paper", "--record", record_path, "--strict"]
                )
        self.assertEqual(1, exit_code)
        self.assertIn("no mapping for column series_ordinal", buf.getvalue())

    def test_proceedings_and_event_dry_run(self):
        """
        test that dry-runs of the proceedings and event mappings show the
        statements of Q141623730 (Vol-4280) and Q141623731 - see issue #17
        """
        test_params = [
            (
                "proceedings",
                {
                    "label": "Proceedings of the CAiSE 2026 Research Projects Exhibition (CAiSE-RPE 2026)",
                    "description": "Proceedings of CAiSE-RPE 2026 workshop",
                    "volume": "4280",
                    "short name": "CAiSE-RPE 2026",
                    "pubDate": "2026-10-02",
                    "title": "Proceedings of the CAiSE 2026 Research Projects Exhibition (CAiSE-RPE 2026)",
                    "ceurwsUrl": "https://ceur-ws.org/Vol-4280/",
                    "language of work or name": "Q1860",
                    "fullWorkUrl": "https://ceur-ws.org/Vol-4280/",
                    "urn": "urn:nbn:de:0074-4280-x",
                },
                [
                    "Q1143604",
                    "Q27230297",
                    "+2026-10-02T00:00:00Z",
                    "P973",
                    "P953",
                    "urn:nbn:de:0074-4280-x",
                ],
            ),
            (
                "event",
                {
                    "label": "CAiSE 2026 Research Projects Exhibition (CAiSE-RPE 2026)",
                    "description": "academic workshop",
                    "instanceof": "Q40444998",
                    "short name": "CAiSE-RPE 2026",
                    "title": "CAiSE 2026 Research Projects Exhibition (CAiSE-RPE 2026)",
                    "start time": "2026-06-08",
                    "end time": "2026-06-12",
                    "locationWikidataId": "Q2028",
                    "countryWikidataId": "Q38",
                },
                [
                    "Q40444998",
                    "+2026-06-08T00:00:00Z",
                    "+2026-06-12T00:00:00Z",
                    "Q2028",
                    "Q38",
                ],
            ),
        ]
        for mapping_name, record, tokens in test_params:
            with self.subTest(mapping=mapping_name):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    record_path = os.path.join(tmp_dir, f"{mapping_name}.yaml")
                    with open(record_path, "w") as record_file:
                        yaml.safe_dump(record, record_file)
                    out = self.run_cmd(
                        ["--mapping", mapping_name, "--record", record_path, "--strict"]
                    )
                if self.debug:
                    print(out)
                for token in tokens:
                    self.assertIn(token, out)

    def test_construct(self):
        """
        test that the command and its parser construct (entry point is wired)
        """
        cmd = EzWdCmd()
        parser = cmd.get_arg_parser()
        self.assertIsNotNone(parser)
