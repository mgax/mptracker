import logging
from flask.ext.script import Manager
from mptracker.scraper.common import get_cached_session
from mptracker import models
from mptracker.common import TablePatcher

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

scraper_manager = Manager()


@scraper_manager.command
def questions():
    from mptracker.scraper.questions import QuestionScraper

    existing = {(q.number, q.date): q for q in models.Question.query}
    person_matcher = models.PersonMatcher()
    n_add = n_update = n_ok = 0

    questions_scraper = QuestionScraper(get_cached_session())
    for question in questions_scraper.run():
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
            'person':    person,
        }

        row = existing[question.number, question.date]

        changed = False
        for k, v in q_data.items():
            if getattr(row, k) != v:
                setattr(row, k, v)
                changed = True

        if changed:
            logger.info('changed %s', row.id)
            n_update += 1

        else:
            n_ok += 1

    logger.info("Created %d, updated %d, found ok %d.", n_add, n_update, n_ok)
    models.db.session.commit()


@scraper_manager.command
def people(year='2012'):
    from mptracker.scraper.people import PersonScraper

    patcher = TablePatcher(models.Person,
                           models.db.session,
                           key_columns=['cdep_id'])

    records = PersonScraper(get_cached_session()).fetch_people(year)

    patcher.update(records)
