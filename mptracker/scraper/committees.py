from mptracker.scraper.common import Scraper, url_args, GenericModel


class Committee(GenericModel):
    pass


class CommitteeScraper(Scraper):

    listing_page_url = \
        'http://www.cdep.ro/pls/parlam/structura.co?cam={chamber_id}&leg=2012'
    committee_url_prefix = \
        'http://www.cdep.ro/pls/parlam/structura.co?'

    def fetch_committees(self):
        for chamber_id in [0, 1, 2]:
            url = self.listing_page_url.format(chamber_id=chamber_id)
            listing_page = self.fetch_url(url)

            for row in listing_page.items('table.tip01 tr[valign=top]'):
                cell = row('td').eq(1)
                link = cell('a').eq(0)
                href = link.attr('href')
                assert href.startswith(self.committee_url_prefix)
                args = url_args(href)
                assert args['leg'] == '2012'
                assert args['cam'] == str(chamber_id)
                yield Committee(
                    cdep_id = int(args['idc']),
                    chamber_id = chamber_id,
                    name = link.text(),
                )
