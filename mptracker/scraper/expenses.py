from pyquery import PyQuery as pq
from mptracker.scraper.common import (Scraper, url_args, GenericModel,
                                      parse_profile_url, parse_date)


class EconScraper(Scraper):
    index_url = 'http://www.cdep.ro/pls/parlam/informatii_economice.home'

    def fetch(self):
        index_page = self.fetch_url(self.index_url)
        headline = index_page.find('#signup')
        tables = headline.find('table')
        tables_months = tables.find('tr')
        url_set = set()

        for link in tables_months.items('td > a'):
            url_set.add(link.attr('href'))
        for url in url_set:
            return self.fetch_month(url)
        #Tested with return, when finished @ yield self.fetch_section(url)

    def fetch_month(self, section_url):
        url_date = url_args(section_url)

        if (url_date['an'] < '2010' or
                (url_date['an'] == '2010' and url_date['lu'] <= '3')):
            return None
        else:
            economical_info_page = self.fetch_url(section_url)
            headline = economical_info_page.find('#pageContent')
            headline_parent = pq(headline.parents('td')[-1])
            table = pq(headline_parent.find('#div-1c'))
            table_items = table.children('ol>li').eq(3).find('a')
            return (self.fetch_table(table_items.attr('href')))

    def fetch_table(self, table_url):
        expenses_page = self.fetch_url(table_url)

        headline = expenses_page.find('.rowh')
        data = []
        table = headline.children()
        for item in table.items():
            data.append(item.text())

        data_table = []
        expenses_table = pq(headline).siblings()
        for column in expenses_table.items():
            if (column.hasClass('row0') or column.hasClass('row1')):
                column_data = []
                for data in column.find('td').items():
                    column_data.append(data.text())

                data_table.append([key, column_data])
            else:
                key = (column.text())
        return data_table
