'''
Created on 2024-03-03

@author: wf
'''
from tests.basetest import BaseTest
from ez_wikidata.wdproperty import WikidataPropertyManager

class TestWikiproperties(BaseTest):
    """
    test the Wikidata properties handling
    """

    def setUp(self, debug=True, profile=True):
        super().setUp(debug, profile)
        
    def testWikidataPropertiesManager(self):
        """
        test the WikidataPropertyManager
        """
        for endpoint_url in ["https://qlever.cs.uni-freiburg.de/api/wikidata"]:
            for lang in ["en","de"]:
                wpm=WikidataPropertyManager()
                props=wpm.fetch_props_for_lang(endpoint_url=endpoint_url,lang=lang)
                if self.debug:
                    print(f"found {len(props)} properties for lang {lang}")
        with_save=self.debug
        if with_save:
            wpm.store_to_cache()    
        
    def test_from_cache(self):
        wpm=WikidataPropertyManager.from_cache()