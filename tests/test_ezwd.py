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
            "series_ordinal": "1",
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
        ]:
            self.assertIn(token, out)

    def test_construct(self):
        """
        test that the command and its parser construct (entry point is wired)
        """
        cmd = EzWdCmd()
        parser = cmd.get_arg_parser()
        self.assertIsNotNone(parser)
