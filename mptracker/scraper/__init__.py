import logging
from flask.ext.script import Manager
from mptracker.scraper.common import get_cached_session
from mptracker import models
from mptracker.common import TablePatcher, fix_local_chars

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

    def get_people():
        person_scraper = PersonScraper(get_cached_session())
        for row in person_scraper.fetch_people(year):
            county_name = row.pop('county_name')
            if county_name:
                ok_name = fix_local_chars(county_name.title())
                if ok_name == "Bistrița-Năsăud":
                    ok_name = "Bistrița Năsăud"
                county = models.County.query.filter_by(name=ok_name).first()
                if county is None:
                    logger.warn("Can't match county name %r", ok_name)
                else:
                    row['county'] = county

            yield row

    patcher.update(get_people())


@scraper_manager.command
def committee_summaries(year=2013):
    from mptracker.scraper.committee_summaries import SummaryScraper

    patcher = TablePatcher(models.CommitteeSummary,
                           models.db.session,
                           key_columns=['pdf_url'])

    summary_scraper = SummaryScraper(get_cached_session(),
                                     get_cached_session('question-pdf'))
    records = summary_scraper.fetch_summaries(year, get_pdf_text=True)

    patcher.update(records)


@scraper_manager.command
def proposals():
    from mptracker.scraper.proposals import ProposalScraper

    proposal_scraper = ProposalScraper(get_cached_session())

    by_cdep_id = {p.cdep_id: p
                  for p in models.Person.query
                  if p.year == '2012'}
    proposals = proposal_scraper.fetch_from_mp_pages(set(by_cdep_id.keys()))

    proposal_patcher = TablePatcher(models.Proposal,
                                    models.db.session,
                                    key_columns=['cdep_serial'])

    person_matcher = models.PersonMatcher()

    sp_updates = sp_added = sp_removed = 0

    with proposal_patcher.process(autoflush=1000) as add:
        for record in proposals:
            if not record.get('cdep_serial'):
                continue # for now
            sponsorships = record.pop('_sponsorships')
            url = record['url']

            result = add(record)
            row = result.row

            new_people = set(by_cdep_id[ci] for ci in sponsorships)
            existing_sponsorships = {sp.person: sp for sp in row.sponsorships}
            to_remove = set(existing_sponsorships) - set(new_people)
            to_add = set(new_people) - set(existing_sponsorships)
            if to_remove:
                logger.info("Removing sponsors: %r",
                            [p.cdep_id for p in to_remove])
                sp_removed += 1
                for p in to_remove:
                    sp = existing_sponsorships[p]
                    models.db.session.delete(sp)
            if to_add:
                logger.info("Adding sponsors: %r",
                            [p.cdep_id for p in to_add])
                sp_added += 1
                for p in to_add:
                    row.sponsorships.append(models.Sponsorship(person=p))

            if to_remove or to_add:
                sp_updates += 1

    logger.info("Updated sponsorship for %d proposals (+%d, -%d)",
                sp_updates, sp_added, sp_removed)
