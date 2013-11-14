from pyquery import PyQuery as pq;
from mptracker.scraper.common import (Scraper, url_args, GenericModel,
                                              parse_profile_url, parse_date)
import unicodedata

class RomaniaCurata(Scraper):

    index_url = "http://verificaintegritatea.romaniacurata.ro/?cat=12"
    
    def fetch_urls(self, current_url):
        
        index_page = self.fetch_url(current_url)
        #this is how we parse each candidate url
        #get .entry-title attribute
        
        candidates_html = index_page.find(".entry-title")
        #d('.entry-title').html().split('title')[0][8:].rstrip()        
        #from pdb import set_trace; set_trace();
        #is there a next page from index_page?

        def has_next_page():
            return index_page.find('.next.page-numbers').attr.href;
        
        for candidate_index in range(len(candidates_html)):
            yield candidates_html.eq(candidate_index)('a').attr('href')
        #this is a trick for handling fetches on every page
        if(has_next_page() != None):    
            yield from self.fetch_urls(has_next_page())
    
    def fetch_treasures(self):
        #now let's fetch treasures
        
        treasures = dict();

        url_set = list(self.fetch_urls(self.index_url))
        
        for url in url_set:
            main_page = self.fetch_url(url)

            name_link = main_page.find('.entry-title').text();
            #names work
            big_treasure = main_page.find('.entry-content')('p')
            
            #print(name_link)
            
            #these lines aren't tested because of unicode errors

            for treasure_index in range(len(big_treasure)):
                #treasures are not marked with <strong>
                small_treasure = big_treasure.eq(treasure_index)
                
                if(small_treasure('strong') == []):
                    print (small_treasure.text())
                    treasures[name_link].update(small_treasure)

        return treasures

