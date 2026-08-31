"""
Created on 2026-06-26

@author: wf
"""

import io
from contextlib import redirect_stdout

from ez_wikidata.ezwd_cmd import EzWdCmd, main
from ez_wikidata.wdproperty import PropertyMappings
from tests.basetest import BaseTest


class TestEzWdCmd(BaseTest):
    """
    test the ezwd command line interface
    """

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

    def test_preview(self):
        """
        test that the dry-run preview shows the statements that would be
        written and warns about record columns the mapping does not cover
        """
        record = {
            "label": "Test Person",
            "description": "test",
            "instanceof": "Q5",
            "occupation": "Q1650915",
            "researchGate": "Test-Person",
            "researchGateTypo": "xyz",
        }
        cmd = EzWdCmd()
        mappings = PropertyMappings.of_name("scholar")
        buf = io.StringIO()
        with redirect_stdout(buf):
            unmapped = cmd.preview(record, mappings)
        out = buf.getvalue()
        self.assertEqual(["researchGateTypo"], unmapped)
        for token in [
            "Test Person",
            "P31 instance of = Q5",
            "P106 occupation = Q1650915",
            "P2038 ResearchGate profile ID = Test-Person",
            "warning: no mapping for column researchGateTypo",
        ]:
            self.assertIn(token, out)

    def test_construct(self):
        """
        test that the command and its parser construct (entry point is wired)
        """
        cmd = EzWdCmd()
        parser = cmd.get_arg_parser()
        self.assertIsNotNone(parser)
