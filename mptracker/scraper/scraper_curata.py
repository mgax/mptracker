from pyquery import PyQuery as pq
from mptracker.scraper.common import (Scraper, url_args, GenericModel,
                                              parse_profile_url, parse_date)

class RomaniaCurata(Scraper):

    index_url = "http://verificaintegritatea.romaniacurata.ro/?cat=12"
    use_cdep_opener = False 
    
    def fetch_urls(self, current_url):
        
        index_page = self.fetch_url(current_url)        
        candidates_html = index_page.find(".entry-title")
        
        has_next_page = index_page.find('.next.page-numbers').attr.href
        
        for candidate_index in range(len(candidates_html)):
            yield candidates_html.eq(candidate_index)('a').attr.href
        #this is a trick for handling fetches on every page
        
        if(has_next_page != None):    
            yield from self.fetch_urls(has_next_page)
    
    def fetch_fortunes(self):
        
        fortunes = dict();
        url_set = self.fetch_urls(self.index_url)
        
        for url in url_set:
            
            main_page = self.fetch_url(url)
            name_link = main_page.find('.entry-title').text()
            big_fortune = main_page.find('.entry-content')('p')
            print(name_link) 
            #next lines aren't tested because of unicode errors
            
            for fortune_index in range(len(big_fortune)):
                #treasures are not marked with <strong>
                small_fortune = big_fortune.eq(fortune_index)
                
                if(small_fortune('strong') == []):
                    fortunes.update( {name_link : small_fortune} )
                    print (small_fortune.text().encode('utf-8'))
        return fortunes
