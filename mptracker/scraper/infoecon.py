from pyquery import PyQuery as pq
from mptracker.scraper.common import (Scraper, url_args, GenericModel,
                                      parse_profile_url, parse_date)


class EconScraper(Scraper):
		index_url = 'http://www.cdep.ro/pls/parlam/informatii_economice.home'

		#Url principal
		def fetch(self):
			#return 'Linkul este : %s' %(self.index_url)
			index_page=self.fetch_url(self.index_url)
			headline=index_page.find('#signup')
			headline_tables=headline.find('table')
			headline_tables_tr=headline_tables.find('tr')
			url_set = set()
	        for link in headline_tables_tr.items('td>a'):
	        	url_set.add(link.attr('href'))

'''    
	        #search in table td > a and url_set[] =href
	        url_set = set()
	        for link in headline_tables_tr.items('td > a'): 
	            url_set.add(link.attr('href'))

	        for url in sorted(url_set):
	            yield self.fetch_section(url)    
   

		#Url secundar -> Aleg doar D.	    
	    def fetch_section(self, section_url):
	        section_page = self.fetch_url(section_url)
	        headline = section_page.find('pageContent')
	        parent_td = pq(headline.parents('td')[-1])
	        mp_table = pq(parent_td.find('div-1c')).children('li').eq(3).find('a')

	        url_set = set()
	        url_set.add(mp_table.attr('href'))

	      
	    #De continuat fetch_table
	    def fetch_table(self,table_url):
	    	table_page=self.fetch_section(table_url)
	    	table_headline=table_page.find('rowh')
	    	table_items=pq(table_headline).siblings('tr')
	    	#tr bgcolor /tr row0 row1
	    	c=[]
	    	for item in table_items.items():
	    		if item.hasClass('row0') or item.hasClass('row1'):
	    			c.append(item)
	    		else:
	    			if c!=Null:
	    				make_scrap(c) #transforma c a.i. sa fie gata de baza de date
	    			c=[]


	   	def make_scrap(self,table):
	   		info = Info(
	   			)
	   		for item in table.items():
'''