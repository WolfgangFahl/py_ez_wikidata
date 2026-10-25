"""
Created on 2026-10-25

@author: wf
"""

import io
from contextlib import redirect_stdout

from ez_wikidata.ezwd_cmd import main
from ez_wikidata.wbtarget import WikibaseTarget
from tests.basetest import BaseTest


class TestWikibaseTarget(BaseTest):
    """
    test using other Wikibase instances than Wikidata via per-target id
    translation - see issue #20
    """

    def setUp(self, debug=True, profile=True):
        BaseTest.setUp(self, debug=debug, profile=profile)

    def run_cmd(self, argv, expected_exit_code: int = 0) -> str:
        """
        run the ezwd command with the given argv and capture stdout
        """
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = main(argv)
        out = buf.getvalue()
        if self.debug:
            print(out)
        self.assertEqual(expected_exit_code, exit_code)
        return out

    def test_of_name(self):
        """
        test loading the bundled targets with their translation tables
        """
        test_params = [
            ("wikidata", "https://www.wikidata.org", "P31", "P31"),
            ("test", "https://test.wikidata.org", "P31", "P82"),
            ("factgrid", "https://database.factgrid.de", "P31", "P2"),
            ("factgrid", "https://database.factgrid.de", "P2456", None),
        ]
        for name, baseurl, wd_id, target_id in test_params:
            with self.subTest(name=name, wd_id=wd_id):
                target = WikibaseTarget.of_name(name)
                self.assertEqual(baseurl, target.baseurl)
                self.assertEqual(target_id, target.translate_id(wd_id))

    def test_of_baseurl(self):
        """
        test finding a target by its baseurl
        """
        target = WikibaseTarget.of_baseurl("https://database.factgrid.de")
        self.assertEqual("factgrid", target.name)
        self.assertIsNone(WikibaseTarget.of_baseurl("https://example.org"))

    def test_example_targets(self):
        """
        test that the scholar example dry-run shows the target's own ids and
        reports the properties without id on the target
        """
        test_params = [
            (
                ["--test"],
                ["P82 instance of: Q497", "P98119", "no id for P6634"],
                ["P31", "P496"],
            ),
            (
                ["--target", "factgrid"],
                ["P2 Instance of: Q7", "P408", "P709"],
                ["P31", "P496", "P6634"],
            ),
        ]
        for target_args, tokens, wd_tokens in test_params:
            with self.subTest(target=target_args):
                out = self.run_cmd(["--mapping", "scholar", "--example"] + target_args)
                for token in tokens:
                    self.assertIn(token, out)
                for wd_token in wd_tokens:
                    self.assertNotIn(f"  {wd_token} ", out)
                self.assertIn("no id for P2456", out)

    def test_example_strict(self):
        """
        test that --strict fails on a property without id on the target
        """
        out = self.run_cmd(
            ["--mapping", "scholar", "--example", "--test", "--strict"],
            expected_exit_code=1,
        )
        self.assertIn("no id for P2456", out)

    def test_unknown_baseurl(self):
        """
        test that a baseurl without translation table is reported instead of
        silently using the Wikidata ids
        """
        out = self.run_cmd(
            ["--mapping", "scholar", "--example", "--baseurl", "https://example.org"]
        )
        self.assertIn("no translation table for https://example.org", out)

    def test_search_target(self):
        """
        test that --search uses the Wikibase of the target
        """
        if self.inPublicCI():
            return
        out = self.run_cmd(["--search", "Human", "--target", "factgrid"])
        self.assertIn("Q7\tHuman", out)

    def test_format_turtle_target(self):
        """
        test that the RDF output uses the namespaces of the target
        """
        out = self.run_cmd(
            ["--mapping", "scholar", "--example", "--target", "factgrid"]
            + ["--format", "turtle"]
        )
        self.assertIn("<https://database.factgrid.de/prop/direct/>", out)
        self.assertIn("wdt:P2 wd:Q7", out)
