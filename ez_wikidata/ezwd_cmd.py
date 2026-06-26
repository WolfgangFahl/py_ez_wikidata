"""
Created on 2026-06-26

ezwd command line interface

@author: wf
"""

import json
from argparse import ArgumentParser, Namespace
from typing import List, Optional

import yaml
from basemkit.base_cmd import BaseCmd

from ez_wikidata.version import Version
from ez_wikidata.wdproperty import PropertyMappings
from ez_wikidata.wdsearch import WikidataSearch
from ez_wikidata.wikidata import Wikidata


class EzWdCmd(BaseCmd):
    """
    command line interface for easy Wikidata access:
    search Wikidata, inspect a named property mapping and create/update a
    Wikidata item from a record using that mapping.
    """

    def __init__(self):
        """
        constructor
        """
        super().__init__(Version())

    def add_arguments(self, parser: ArgumentParser) -> ArgumentParser:
        """
        add the ezwd specific arguments

        Args:
            parser(ArgumentParser): the parser to add arguments to
        """
        super().add_arguments(parser)
        parser.add_argument(
            "-s",
            "--search",
            help="search Wikidata for the given text and show candidate Q-ids",
        )
        parser.add_argument(
            "-m",
            "--mapping",
            help="name of the bundled property mapping to use (e.g. scholar)",
        )
        parser.add_argument(
            "--list-mappings",
            action="store_true",
            help="list the columns of the mapping given via --mapping",
        )
        parser.add_argument(
            "-r",
            "--record",
            help="YAML or JSON file with the record to create as a Wikidata item",
        )
        parser.add_argument(
            "--lang",
            default="en",
            help="language to use (default: %(default)s)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=9,
            help="maximum number of search results (default: %(default)s)",
        )
        parser.add_argument(
            "-w",
            "--write",
            action="store_true",
            help="actually write to Wikidata (default: dry-run, nothing is written)",
        )
        return parser

    def handle_args(self, args: Namespace) -> bool:
        """
        handle the parsed arguments

        Args:
            args(Namespace): the parsed arguments

        Returns:
            bool: True if the arguments were handled
        """
        handled = super().handle_args(args)
        if handled:
            return True
        if args.search:
            self.search(args.search, args.lang, args.limit)
        elif args.mapping and args.list_mappings:
            self.list_mapping(args.mapping)
        elif args.mapping and args.record:
            self.create(args.mapping, args.record, args.lang, args.write)
        else:
            self.parser.print_help()
        return True

    def search(self, search_for: str, lang: str, limit: int):
        """
        search Wikidata and print candidate q-id / label / description rows

        Args:
            search_for(str): the text to search for
            lang(str): the language to use
            limit(int): the maximum number of results
        """
        wds = WikidataSearch(language=lang)
        for qid, label, desc in wds.searchOptions(search_for, limit=limit):
            print(f"{qid}\t{label}\t{desc}")

    def list_mapping(self, name: str):
        """
        list the columns of the named property mapping

        Args:
            name(str): the mapping name (e.g. scholar)
        """
        mappings = PropertyMappings.of_name(name)
        print(f"{mappings.name}: {mappings.description or ''}")
        for column, pm in mappings.mappings.items():
            print(f"  {column}\t{pm.propertyId}\t{pm.propertyType}\t{pm.propertyName}")

    def load_record(self, record_path: str) -> dict:
        """
        load a record from a YAML or JSON file

        Args:
            record_path(str): path to the record file

        Returns:
            dict: the loaded record
        """
        with open(record_path) as record_file:
            if record_path.endswith(".json"):
                record = json.load(record_file)
            else:
                record = yaml.safe_load(record_file)
        return record

    def create(self, name: str, record_path: str, lang: str, write: bool):
        """
        create (or dry-run) a Wikidata item from the given record using the
        named property mapping

        Args:
            name(str): the mapping name (e.g. scholar)
            record_path(str): path to the YAML/JSON record file
            lang(str): the language to use
            write(bool): if True actually write to Wikidata
        """
        mappings = PropertyMappings.of_name(name)
        record = self.load_record(record_path)
        wd = Wikidata()
        if write:
            wd.loginWithCredentials()
        result = wd.add_record(
            record, list(mappings.mappings.values()), lang=lang, write=write
        )
        mode = "wrote" if write else "dry-run"
        if result.errors:
            for column, error in result.errors.items():
                print(f"error for {column}: {error}")
        if result.qid:
            print(f"{mode} {result.qid}: {wd.baseurl}/wiki/{result.qid}")
        else:
            print(f"{mode} (no item id; use --write to create on Wikidata)")


def main(argv: Optional[List[str]] = None) -> int:
    """
    main entry point for the ezwd command line tool

    Args:
        argv(list): the command line arguments (defaults to sys.argv)

    Returns:
        int: the exit code
    """
    cmd = EzWdCmd()
    exit_code = cmd.run(argv)
    return exit_code


if __name__ == "__main__":
    main()
