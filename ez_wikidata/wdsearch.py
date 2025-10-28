"""
Created on 2022-07-24

@author: wf
"""

import json
import logging
import os
from typing import List, Tuple
import urllib.parse
import urllib.request


class WikidataSearch(object):
    """
    Wikidata Search API wrapper
    """

    def __init__(self, language: str="en", timeout: float=2.0):
        """
        Constructor

        Args:
            language(str): the language to use e.g. en/fr
            timeout(float): maximum time to wait for result
        """
        self.language = language
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)

    def searchOptions(
        self, searchFor: str, limit: int=9
    ) -> List[Tuple[str, str, str]]:
        """
        Search and return a list of qid, itemLabel, description tuples.

        Args:
            searchFor (str): the string to search for.
            limit (int): the maximum amount of results to return.

        Returns:
            List[Tuple[str, str, str]]:
            A list of tuples containing
            qid, itemLabel, and description.
        """
        options = []
        srlist = self.search(searchFor, limit)
        if srlist is not None:
            for sr in srlist:
                qid = sr["id"]
                itemLabel = sr["label"]
                desc = ""
                if "display" in sr:
                    display = sr["display"]
                    if "description" in display:
                        desc = display["description"]["value"]
                options.append(
                    (
                        qid,
                        itemLabel,
                        desc,
                    )
                )
        return options

    def make_wikidata_request(self, apisearch: str):
        """Make HTTP request to Wikidata API with proper user agent"""
        req = urllib.request.Request(
            apisearch,
            headers={'User-Agent': 'wdsearch/1.0 (webmaster@bitplan.com)'}
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as url:
            return json.loads(url.read().decode())

    def search(self, searchFor: str, limit: int = 9) -> List[dict]:
        """
        Search for Wikidata entities.

        Args:
            searchFor(str): the string to search for
            limit(int): the maximum amount of results to search for

        Returns:
            List[dict]: list of search result dictionaries, or error pseudo-result on failure
        """
        searchResult = {}
        try:
            apiurl = f"https://www.wikidata.org/w/api.php?action=wbsearchentities&language={self.language}&uselang={self.language}&format=json&limit={limit}&search="
            searchEncoded = urllib.parse.quote_plus(searchFor)
            apisearch = apiurl + searchEncoded
            rawSearchResult = self.make_wikidata_request(apisearch)
            searchResult = rawSearchResult["search"]
        except Exception as error:
            self.logger.error(f"Error searching for '{searchFor}': {error}", exc_info=True)
            searchResult = [{
            'id': 'ERROR',
            'label': f'⚠️ Search failed: {type(error).__name__}',
            'description': str(error),
            'display': {
                'label': {'value': f'⚠️ Search failed: {type(error).__name__}', 'language': self.language},
                'description': {'value': str(error), 'language': self.language}
            }
        }]
        return searchResult

    def getProperties(self):
        """
        get the Wikidata Properties
        """
        scriptdir = os.path.dirname(__file__)
        jsonPath = f"{scriptdir}/resources/wdprops.json"
        with open(jsonPath) as jsonFile:
            props = json.load(jsonFile)
        return props
