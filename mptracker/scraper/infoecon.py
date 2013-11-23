from pyquery import PyQuery as pq
from mptracker.scraper.common import (Scraper, url_args, GenericModel,
                                      parse_profile_url, parse_date)


class EconScraper(Scraper):
	index_url = 'http://www.cdep.ro/pls/parlam/informatii_economice.home'

	def fetch(self):
		index_page = self.fetch_url(self.index_url)
		headline = index_page.find('#signup')
		headline_tables = headline.find('table')
		headline_tables_tr = headline_tables.find('tr')
		url_set = set()

		for link in headline_tables_tr.items('td > a'):
			url_set.add(link.attr('href'))
		for url in url_set:
			return self.fetch_section(url) 
		#Tested with return, when finished @ yield self.fetch_section(url)   


	def fetch_section(self,section_url):
		check_forD = (section_url.split('?'))[1].split('&')
		items = []
		for item in check_forD:
			items.append(item.split('='))

		if (items[1][1]<'2010' or (items[1][1]=='2010' and items[2][1]<='s3') ):
			return None 
		else:
			section_page = self.fetch_url(section_url)
			headline = section_page.find('#pageContent')
			parent_td = pq(headline.parents('td')[-1])
			mp_table = pq(parent_td.find('#div-1c')).children('ol>li').eq(3).find('a')
			url_set = set()
			url_set.add(mp_table.attr('href'))
			for url in url_set:
				return self.fetch_table(url) 

	def fetch_table(self,table_url):
		print(table_url)
		table_page = self.fetch_url(table_url)

		table_headline = table_page.find('.rowh')
		data = []
		table = table_headline.children()
		for item in table.items():
			data.append(item.text().encode('utf-8'))

		table_data = []

		table_trs = pq(table_headline).siblings()
		for item in table_trs.items():
			if (item.hasClass('row0') or item.hasClass('row1')):
				td_data = []
				for td in item.find('td').items():
					td_data.append(td.text().encode('utf-8'))

				table_data.append([key,td_data])
			else:
				key = (item.text().encode('utf-8'))
		return table_data
