from pyquery import PyQuery as pq
from mptracker.scraper.common import (Scraper, url_args, GenericModel,
                                      parse_profile_url, parse_date)


class EconScraper(Scraper):
		index_url = 'http://www.cdep.ro/pls/parlam/informatii_economice.home'


		def fetch(self):
			index_page=self.fetch_url(self.index_url)
			headline=index_page.find('#signup')
			headline_tables=headline.find('table')
			headline_tables_tr=headline_tables.find('tr')
			url_set = set()

			for link in headline_tables_tr.items('td > a'):
				url_set.add(link.attr('href'))
			for url in url_set:
				return self.fetch_section(url) #Test cu return, a se modifica cu la final @ yield self.fetch_section(url)   


		def fetch_section(self, section_url):
			print (section_url)
			section_page = self.fetch_url(section_url)
			headline = section_page.find('#pageContent')
			parent_td = pq(headline.parents('td')[-1])
			mp_table = pq(parent_td.find('#div-1c')).children('ol>li').eq(3).find('a')
			#TODO: NU TOATE AU SI VARIANTA D
			url_set = set()
			url_set.add(mp_table.attr('href'))
			for url in url_set:
				return self.fetch_table(url) #Vezi comment line 20

		def fetch_table(self,table_url):
			print(table_url)
			table_page = self.fetch_url(table_url)
			table_headline = table_page.find('.rowh') #Dictionary Key's
			data=dict()
			data.update({'ky':'&nbsp'}) #Get Dict keys.Last.
			print (data)
			print(table_headline.items())


			table_trs = pq(table_headline).siblings()
			table_items = list(table_trs.items())
	    	#tr bgcolor (delimit) -> tr row0,tr row1
			