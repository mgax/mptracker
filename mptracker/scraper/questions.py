""" Fetch and parse questions & interpellations """

import sys
import re
from datetime import datetime
import logging
from path import path
from flask import json
from pyquery import PyQuery as pq
from mptracker.scraper.common import (Scraper, pqitems, get_cached_session,
                                      parse_cdep_id, never)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


with open(path(__file__).parent / 'question_exceptions.json') as f:
    exceptions = json.load(f)
    url_skip = set(exceptions['url_skip'])
    pdf_url_skip = set(exceptions['pdf_url_skip'])


class QuestionScraper(Scraper):

    title_pattern = re.compile(r'^(?P<type>Întrebarea|Interpelarea) '
                               r'(adresată .*)?'
                               r'nr\.')
    types = {
        'Întrebarea': 'question',
        'Interpelarea': 'interpelation',
    }

    def __init__(self, skip=never, **kwargs):
        self.skip = skip
        return super().__init__(**kwargs)

    def normalize_space(self, text):
        return re.sub(r'\s+', ' ', text)

    def parse_date_dmy(self, text):
        return datetime.strptime(text, '%d-%m-%Y').date()

    def person_from_td(self, td):
        for link in pqitems(td, 'a'):
            href = link.attr('href')
            if href.startswith('http://www.cdep.ro/pls/'
                               'parlam/structura.mp?'):
                (year, number) = parse_cdep_id(href)
                return (link.text(), year, number)

    def extract_answer(self, rows):
        for row in list(rows):
            text = self.normalize_space(row.text())
            if text == "Textul răspunsului: fişier PDF":
                value = pq(row[0][1])
                link = list(pqitems(value, 'a'))[-1]
                assert link.text() == "fişier PDF"
                pdf_url = link.attr('href')
                return {"pdf_url": pdf_url}

    def get_question(self, href):
        page = self.fetch_url(href)
        heading = page('#pageHeader .pageHeaderLinks').text()
        heading_m = self.title_pattern.match(heading)
        assert heading_m is not None, "Could not parse heading %r" % heading
        question = {}
        question['type'] = self.types[heading_m.group('type')]

        question['url'] = href
        question['title'] = page('.headline').text()

        rows = iter(pqitems(page, '#pageContent > dd > table > tr'))
        assert (self.normalize_space(next(rows).text()) ==
                'Informaţii privind interpelarea')

        question['pdf_url'] = None
        question['addressee'] = []
        question['method'] = None
        question['person'] = []

        label_text = None

        for row in rows:
            norm_text = self.normalize_space(row.text())
            if norm_text == '':
                continue
            elif norm_text == 'Informaţii privind răspunsul':
                answer = self.extract_answer(rows)
                if answer:
                    question['answer'] = answer
                break

            [label, value] = [pq(el) for el in row[0]]
            new_label_text = label.text()
            if new_label_text:
                label_text = new_label_text
            else:
                if label_text not in ['Adresanţi:', 'Destinatari:']:
                    continue

            if label_text == 'Nr.înregistrare:':
                question['number'] = value.text()
            elif label_text == 'Data înregistrarii:':
                question['date'] = self.parse_date_dmy(value.text())
            elif label_text == 'Mod adresare:':
                question['method'] = value.text()
            elif label_text in ['Destinatar:', 'Destinatari:']:
                ministry_el = list(pqitems(value, 'b'))[0]
                question['addressee'].append(ministry_el.text())
            elif label_text == 'Adresant:' or label_text == 'Adresanţi:':
                question['person'].append(self.person_from_td(value))
            elif label_text == 'Textul intervenţiei:':
                link = list(pqitems(value, 'a'))[-1]
                assert link.text() == "fişier PDF"
                pdf_url = link.attr('href')
                if pdf_url not in pdf_url_skip:
                    question['pdf_url'] = pdf_url

        question_id = '{q[date]}-{q[number]}'.format(q=question)
        patch = exceptions['patch'].get(question_id, {})
        question.update(patch)
        return question

    def run(self, year):
        index = self.fetch_url('http://www.cdep.ro/pls/parlam/'
                               'interpelari.lista?tip=&dat={year}&idl=1'
                               .format(year=year))
        for link in pqitems(index, '#pageContent table a'):
            href = link.attr('href')
            if href in url_skip:
                continue
            assert href.startswith('http://www.cdep.ro/pls/'
                                   'parlam/interpelari.detalii')

            if self.skip(href):
                logger.debug('skipping %r', href)
            else:
                yield self.get_question(href)
