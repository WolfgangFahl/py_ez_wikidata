"""
Created on 2026-06-26

@author: wf
"""

import io
from contextlib import redirect_stdout

from ez_wikidata.ezwd_cmd import EzWdCmd, main
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

    def test_construct(self):
        """
        test that the command and its parser construct (entry point is wired)
        """
        cmd = EzWdCmd()
        parser = cmd.get_arg_parser()
        self.assertIsNotNone(parser)
