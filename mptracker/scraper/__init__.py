import logging
from flask.ext.script import Manager
from mptracker.scraper.common import get_cached_session, create_session
from mptracker import models
from mptracker.common import TablePatcher, fix_local_chars

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

scraper_manager = Manager()


@scraper_manager.command
def questions(year='2013', reimport_existing=False):
    from mptracker.scraper.questions import QuestionScraper

    if reimport_existing:
        known_urls = set()
    else:
        known_urls = set(q.url for q in models.Question.query)

    def skip_question(url):
        return url in known_urls

    questions_scraper = QuestionScraper(
            session=create_session(cache_name='page-cache', throttle=0.5),
            skip=skip_question)

    mandate_lookup = models.MandateLookup()

    question_patcher = TablePatcher(models.Question,
                                    models.db.session,
                                    key_columns=['number', 'date'])

    new_ask_rows = 0

    with question_patcher.process() as add:
        for question in questions_scraper.run(int(year)):
            person_list = question.pop('person')
            question['addressee'] = '; '.join(question['addressee'])
            q = add(question).row

            old_asked = {ask.mandate_id: ask for ask in q.asked}
            for name, person_year, person_number in person_list:
                mandate = mandate_lookup.find(name, person_year, person_number)
                if mandate.id in old_asked:
                    old_asked.pop(mandate.id)

                else:
                    ask = models.Ask(mandate=mandate)
                    q.asked.append(ask)
                    ask.set_meta('new-ask', True)
                    logger.info("Adding ask for %s: %s", q, mandate)
                    new_ask_rows += 1

            assert not old_asked

    if new_ask_rows:
        logger.info("Added %d ask records", new_ask_rows)


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
def proposals(dry_run=False):
    from mptracker.scraper.proposals import ProposalScraper

    proposal_scraper = ProposalScraper(create_session(cache_name='page-cache',
                                                      throttle=0.5))

    def cdep_id(mandate):
        return (mandate.year, mandate.cdep_number)

    by_cdep_id = {cdep_id(m): m
                  for m in models.Mandate.query
                  if m.year == 2012}

    chamber_by_slug = {c.slug: c for c in models.Chamber.query}

    proposals = proposal_scraper.fetch_from_mp_pages(set(by_cdep_id.keys()))

    proposal_patcher = TablePatcher(models.Proposal,
                                    models.db.session,
                                    key_columns=['combined_id'])

    sp_updates = sp_added = sp_removed = 0

    with proposal_patcher.process(autoflush=1000, remove=True) as add:
        for record in proposals:
            if 'decision_chamber' in record:
                slug = record.pop('decision_chamber')
                record['decision_chamber'] = chamber_by_slug[slug]

            sponsorships = record.pop('_sponsorships')
            url = record['url']

            result = add(record)
            row = result.row

            new_people = set(by_cdep_id[ci] for ci in sponsorships)
            existing_sponsorships = {sp.mandate: sp for sp in row.sponsorships}
            to_remove = set(existing_sponsorships) - set(new_people)
            to_add = set(new_people) - set(existing_sponsorships)
            if to_remove:
                logger.info("Removing sponsors %s: %r", row.combined_id,
                            [cdep_id(m) for m in to_remove])
                sp_removed += 1
                for m in to_remove:
                    sp = existing_sponsorships[m]
                    models.db.session.delete(sp)
            if to_add:
                logger.info("Adding sponsors %s: %r", row.combined_id,
                            [cdep_id(m) for m in to_add])
                sp_added += 1
                for m in to_add:
                    row.sponsorships.append(models.Sponsorship(mandate=m))

            if to_remove or to_add:
                sp_updates += 1

        if dry_run:
            models.db.session.rollback()

    logger.info("Updated sponsorship for %d proposals (+%d, -%d)",
                sp_updates, sp_added, sp_removed)


@scraper_manager.command
def import_person_xls(xls_path):
    from mptracker.scraper.person_xls import read_person_xls

    mandate_lookup = models.MandateLookup()

    people_data = []
    committees = {}
    committee_memberships = []
    groups = {}
    group_memberships = []

    mandate_patcher = TablePatcher(models.Mandate,
                                   models.db.session,
                                   key_columns=['year', 'cdep_number'])
    with mandate_patcher.process() as add:
        for record in read_person_xls(xls_path):
            mandate = mandate_lookup.find(record.pop('name'), record['year'],
                                          record['cdep_number'])
            person_data = record.pop('person_data')
            person_data['id'] = mandate.person_id
            people_data.append(person_data)
            mandate_committees = record.pop('committees')
            mp_group = record.pop('mp_group')
            mandate = add(record).row
            for data in mandate_committees:
                committees[data['name']] = None
                committee_memberships.append(
                    (mandate.id, data['name'], data['role']))
            groups[mp_group['short_name']] = None
            group_memberships.append(
                    (mandate.id, mp_group['short_name'], mp_group['role']))

    person_patcher = TablePatcher(models.Person,
                                  models.db.session,
                                  key_columns=['id'])
    with person_patcher.process() as add:
        for person_data in people_data:
            add(person_data)

    committee_patcher = TablePatcher(models.MpCommittee,
                                     models.db.session,
                                     key_columns=['name'])
    with committee_patcher.process() as add:
        for name in list(committees):
            mp_committee = add({'name': name}).row
            committees[name] = mp_committee.id

    committee_membership_patcher = TablePatcher(models.MpCommitteeMembership,
            models.db.session, key_columns=['mandate_id', 'mp_committee_id'])
    with committee_membership_patcher.process() as add:
        for mandate_id, name, role in committee_memberships:
            add({
                'mandate_id': mandate_id,
                'mp_committee_id': committees[name],
                'role': role,
            })

    mp_group_patcher = TablePatcher(models.MpGroup,
                                    models.db.session,
                                    key_columns=['short_name'])
    with mp_group_patcher.process() as add:
        for short_name in list(groups):
            mp_group = add({'short_name': short_name}).row
            groups[short_name] = mp_group.id

    mp_group_membership_patcher = TablePatcher(models.MpGroupMembership,
            models.db.session, key_columns=['mandate_id', 'mp_group_id'])
    with mp_group_membership_patcher.process() as add:
        for mandate_id, name, role in group_memberships:
            add({
                'mandate_id': mandate_id,
                'mp_group_id': groups[name],
                'role': role,
            })
