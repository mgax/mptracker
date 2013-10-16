import logging
from pyquery import PyQuery as pq
from mptracker.scraper.common import (Scraper, GenericModel, url_args,
                                      parse_profile_url)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class VotingSession(GenericModel):
    pass


class Vote(GenericModel):
    pass


def parse_choice(text):
    if text == 'DA':
        return 'yes'
    elif text == 'NU':
        return 'no'
    elif text == 'Abţinere':
        return 'abstain'
    elif text == '-':
        return 'novote'
    else:
        raise RuntimeError("Unknown vote choice %r" % text)


class VoteScraper(Scraper):

    DAY_URL = 'http://www.cdep.ro/pls/steno/evot.data?dat=%s'
    VOTE_URL = 'http://www.cdep.ro/pls/steno/evot.nominal?idv=%d'

    def scrape_day(self, day):
        url = self.DAY_URL % day.strftime('%Y%m%d')
        page = self.fetch_url(url)
        table = page.find('#pageContent table')
        for link in table.items('td:nth-child(1) a'):
            href = link.attr('href')
            assert href.startswith('http://www.cdep.ro/pls/'
                                   'steno/evot.nominal?idv=')
            vote_cdeppk = url_args(href).get('idv', type=int)
            yield self.scrape_vote(vote_cdeppk)
            break

    def scrape_vote(self, vote_cdeppk):
        url = self.VOTE_URL % vote_cdeppk
        page = self.fetch_url(url)
        subject_label = list(page.items(':contains("Subiect vot:")'))[0]
        subject_td = list(subject_label.parent().items('td'))[1]
        voting_session = VotingSession(
            cdeppk=vote_cdeppk,
            subject=subject_td.text(),
            votes=[],
            proposal_cdeppk=None,
        )
        proposal_link = subject_td.find('a[target=PROIECTE]')
        if proposal_link:
            href = proposal_link.attr('href')
            assert href.startswith('http://www.cdep.ro/pls/proiecte'
                                   '/upl_pck.proiect?idp=')
            args = url_args(href)
            voting_session.proposal_cdeppk = args.get('idp', type=int)

        td_nr_crt = page.find(':contains("Nr. Crt.")')
        table = pq(td_nr_crt.parents().filter('table')[-1])
        for row in list(table.items('tr'))[1:]:
            link = row.find('a')
            (year, chamber, number) = parse_profile_url(link.attr('href'))
            assert chamber == 2
            choice_td = list(row.items('td'))[-1]
            vote = Vote(
                mandate_year=year,
                mandate_number=number,
                mandate_name=link.text(),
                choice=parse_choice(choice_td.text()),
            )
            voting_session.votes.append(vote)

        return voting_session
