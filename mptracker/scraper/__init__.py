import logging
from flask.ext.script import Manager
from mptracker.scraper.common import get_cached_session
from mptracker import models
from mptracker.common import TablePatcher

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

scraper_manager = Manager()


@scraper_manager.command
def questions(year='2013'):
    from mptracker.scraper.questions import QuestionScraper

    patcher = TablePatcher(models.Question,
                           models.db.session,
                           key_columns=['number', 'date'])

    person_matcher = models.PersonMatcher()

    def get_questions():
        questions_scraper = QuestionScraper(get_cached_session())
        for question in questions_scraper.run(year):
            person = person_matcher.get_person(question.person_name,
                                               question.person_cdep_id,
                                               strict=True)
            q_data = {
                'number':    question.number,
                'type':      question.q_type,
                'method':    question.method,
                'title':     question.title,
                'url':       question.url,
                'pdf_url':   question.pdf_url,
                'addressee': '; '.join(question.addressee),
                'date':      question.date,
                'person_id': person.id,
            }
            yield q_data

    patcher.update(get_questions())


@scraper_manager.command
def people(year='2012'):
    from mptracker.scraper.people import PersonScraper

    patcher = TablePatcher(models.Person,
                           models.db.session,
                           key_columns=['cdep_id'])

    records = PersonScraper(get_cached_session()).fetch_people(year)

    patcher.update(records)


@scraper_manager.command
def committee_summaries(year=2013):
    from mptracker.scraper.committee_summaries import SummaryScraper

    records = SummaryScraper(get_cached_session()).fetch_summaries(year)
    for record in records:
        print(record)
