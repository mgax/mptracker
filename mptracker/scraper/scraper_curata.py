from pyquery import PyQuery as pq
from mptracker.scraper.common import (Scraper, url_args, GenericModel,
                                      parse_profile_url, parse_date)
from mptracker.scraper.common import create_throttle


class RomaniaCurata(Scraper):

    index_url = "http://verificaintegritatea.romaniacurata.ro/?cat=12"
    use_cdep_opener = False

    def fetch_urls(self, current_url):
        index_page = self.fetch_url(current_url)
        candidates_html = index_page.find(".entry-title")

        next_page = index_page.find('.next.page-numbers').attr.href

        for candidate_index in range(len(candidates_html)):
            yield candidates_html.eq(candidate_index)('a').attr.href

        if next_page != None:
            yield from self.fetch_urls(next_page)

    def fetch_fortunes(self):
        url_set = self.fetch_urls(self.index_url)
        result = []

        for url in url_set:
            print(url)
            create_throttle(20)
            main_page = self.fetch_url(url)

            name_link = main_page.find('.entry-title').text()
            big_fortune = main_page.find('.entry-content')('p')
            splitted_name = name_link.split(" ")
            #we reverse the order of names of a MP for matching to database
            best_name = splitted_name[-1] + " " + \
                    (" ".join(splitted_name[: len(splitted_name) - 1]))

            total_fortunes = []

            for fortune_index in range(len(big_fortune)):
                small_fortune = big_fortune.eq(fortune_index)
                if fortune_index <= 2:
                    continue
                total_fortunes.append(small_fortune.text())
            result.append((best_name, total_fortunes))
        return result
