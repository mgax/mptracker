import logging
from datetime import timedelta, date, datetime
from collections import defaultdict
import re
import tempfile
from contextlib import contextmanager
import flask
from flask.ext.script import Manager
from psycopg2.extras import DateRange
from path import path
from pathlib import Path
import requests
from mptracker.scraper.common import get_cached_session, create_session, \
                                     get_gdrive_csv, parse_interval
from mptracker import models
from mptracker.common import parse_date, model_to_dict, url_args, almost_eq, \
                             generate_slug, iter_file, calculate_md5, temp_dir
from mptracker.patcher import TablePatcher

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

scraper_manager = Manager()

ONE_DAY = timedelta(days=1)

TERM_INTERVAL = {
    1990: DateRange(date(1990,  6, 18), date(1992, 10, 21)),
    1992: DateRange(date(1992, 10, 21), date(1996, 11, 22)),
    1996: DateRange(date(1996, 11, 22), date(2000, 12, 11)),
    2000: DateRange(date(2000, 12, 11), date(2004, 12, 13)),
    2004: DateRange(date(2004, 12, 13), date(2008, 12, 15)),
    2008: DateRange(date(2008, 12, 15), date(2012, 12, 19)),
    2012: DateRange(date(2012, 12, 19), date(2016, 12, 21)),
    2016: DateRange(date(2016, 12, 21), None),
}

TERM_2016_START = TERM_INTERVAL[2016].lower

CONTROVERSY_CSV_KEY = '1oCBeyNZc6OxIDJTI25wCeEkIEzkxf6qAwhcE69eDKWY'
POSITION_PONTA2_CSV_KEY = '0AlBmcLkxpBOXdFFfTGZmWklwUl9RSm1keTdNRjFxb1E'
POSITION_PONTA3_CSV_KEY = '0AlBmcLkxpBOXdGhMT0h2Vl9lWENlLUpJZm5jZUpYNlE'
POSITION_BIROU_CDEP_CSV_KEY = '0AlBmcLkxpBOXdDFKblpaRnRLNDcxSGotT3dhaWpYYUE'
CABINET_PARTY_CSV_KEY = '0AlBmcLkxpBOXdEpZVzZ5MUNvb004b0Z3UGFZUjdzMUE'
POLICY_DOMAIN_CSV_KEY = '0AlBmcLkxpBOXdGNXcUtNZ2xHYlpEa1NvWmg2MUNBYVE'
STOP_WORDS_CSV_KEY = '0AlBmcLkxpBOXdDRtTExMWDh1Mm1IQ3dVQ085RkJudGc'
MINORITIES_CSV_KEY = '0Ao01Fbm0wOCAdC1neEk0RXV1Z05hRG9QU2FPTlNYZ0E'
COMMITTEE_ROLL_CALL_CSV_KEY = '1w4IufznSMLMxMOxfS-ggp3IwXePEoDHiTAjAsHgMOpE'
PROPOSAL_CONTROVERSY_CSV_KEY = '1gsEHB8PhMMgEVJEv-yCBopFl2aMfnXg_JVaJ1aUgLpI'
MEMBER_COUNT_CSV_KEY = '13FcF2cCqM7OL0ML9UFchyOnn9uUjYTs7RFIIvLFztFs'
PICTURES_FOLDER_KEY = '0B1BmcLkxpBOXVGZyNHhqc0tWZkk'
COMMITTEE_POLICY_CSV_KEY = '0AlBmcLkxpBOXdHQ5clB4a1hyUUxlTE5pTmNKa0ZzYmc'


@contextmanager
def log_to_sentry():
    try:
        yield
    except:
        sentry = flask.current_app.extensions.get('sentry')
        if sentry:
            sentry.client.captureException()
        raise


def _get_config_cache_name():
    return flask.current_app.config.get('PAGE_CACHE')


@scraper_manager.command
def get_questions(
        year='2017',
        existing_reimport=False,
        cache_name=None,
        throttle=None,
        autoanalyze=False,
        unanswered_reimport=False
        ):
    from mptracker.scraper.questions import QuestionScraper
    from mptracker.questions import ocr_question, ocr_answer
    from mptracker.policy import calculate_question

    if existing_reimport:
        known_urls = set()
    else:
        if unanswered_reimport:
            url_query = (
                models.db.session.query(models.Question.url)
                .outerjoin(models.Answer)
                .filter(models.Answer.question_id != None)
            )

        else:
            url_query = models.db.session.query(models.Question.url)

        known_urls = set(row[0] for row in url_query)

    def skip_question(url):
        return url in known_urls

    http_session = create_session(cache_name=cache_name or
                                       _get_config_cache_name(),
                                  throttle=throttle and float(throttle),
                                  counters=True)
    questions_scraper = QuestionScraper(session=http_session,
                                        skip=skip_question)

    mandate_lookup = models.MandateLookup()

    question_patcher = TablePatcher(models.Question,
                                    models.db.session,
                                    key_columns=['number', 'date'])

    answer_patcher = TablePatcher(models.Answer,
                                  models.db.session,
                                  key_columns=['question_id'])

    new_ask_rows = 0

    changed_questions = []
    changed_answers = []

    with question_patcher.process() as add, \
         answer_patcher.process() as add_answer:
        for question in questions_scraper.run(int(year)):
            person_list = question.pop('person')
            question['addressee'] = '; '.join(question['addressee'])
            answer_data = question.pop('answer', None)
            result = add(question)
            q = result.row

            old_asked = {ask.mandate_id: ask for ask in q.asked}
            for name, person_year, person_number in person_list:
                mandate = mandate_lookup.find(name, person_year, person_number)
                if mandate.id in old_asked:
                    old_asked.pop(mandate.id)

                else:
                    ask = models.Ask(mandate=mandate)
                    q.asked.append(ask)
                    ask.set_meta('new', True)
                    logger.info("Adding ask for %s: %s", q, mandate)
                    new_ask_rows += 1

            if result.is_changed:
                changed_questions.append(q)

            if old_asked:
                logger.warn("Removing %d old 'ask' records", len(old_asked))
                for ask in old_asked.values():
                    models.db.session.delete(ask)

            if answer_data:
                assert q.id is not None
                answer_data['question_id'] = q.id
                answer_result = add_answer(answer_data)
                if answer_result.is_changed:
                    changed_answers.append(answer_result.row)

    models.db.session.commit()

    if new_ask_rows:
        logger.info("Added %d ask records", new_ask_rows)

    counters = http_session.counters
    logger.info("HTTP: %d kb in %s requests, %.2f seconds",
                counters['bytes'] / 1024, counters['requests'],
                counters['download_time'].total_seconds())

    if autoanalyze:
        logger.info("Scheduling jobs for %d questions", len(changed_questions))
        for question in changed_questions:
            if question.pdf_url:
                ocr_question.delay(question.id, autoanalyze=True)

            if question.policy_domain_id is None:
                calculate_question.delay(question.id)

        logger.info("Scheduling jobs for %d answers", len(changed_answers))
        for answer in changed_answers:
            ocr_answer.delay(answer.id)


@scraper_manager.command
def get_people(
    year='2016',
    cache_name=None,
    throttle=None,
    no_commit=False,
    add_people=False,
):
    from mptracker.scraper.people import MandateScraper

    http_session = create_session(
        cache_name=cache_name or _get_config_cache_name(),
        throttle=throttle and float(throttle),
    )
    mandate_scraper = MandateScraper(http_session)

    mandate_patcher = TablePatcher(
        models.Mandate,
        models.db.session,
        key_columns=['year', 'cdep_number'],
    )

    person_patcher = TablePatcher(
        models.Person,
        models.db.session,
        key_columns=['id'],
    )

    term_interval = TERM_INTERVAL[int(year)]
    new_people = 0
    chamber_by_slug = {c.slug: c for c in models.Chamber.query}

    with mandate_patcher.process() as add_mandate, \
         person_patcher.process() as add_person:
        for mandate in mandate_scraper.fetch(year):
            row = mandate.as_dict([
                'year',
                'cdep_number',
                'minority',
                'college',
                'constituency',
                'picture_url',
            ])
            assert mandate.chamber_number == 2
            row['chamber_id'] = chamber_by_slug['cdep'].id
            start_date = mandate.start_date or term_interval.lower
            end_date = mandate.end_date or term_interval.upper or date.max
            row['interval'] = DateRange(start_date, end_date)

            person = (
                models.Person.query
                    .filter_by(name=mandate.person_name)
                    .first())

            if person is None:
                if add_people:
                    person = models.Person(
                        name=mandate.person_name,
                        slug=generate_slug(mandate.person_name),
                    )
                    models.db.session.add(person)
                    models.db.session.flush()
                    new_people += 1

                else:
                    raise RuntimeError("Can't find person named %r"
                                       % mandate.person_name)

            assert not add_person({
                'id': person.id,
                'first_name': mandate.person_first_name,
                'last_name': mandate.person_last_name,
            }).is_new

            row['person_id'] = person.id

            if not mandate.minority:
                county = (
                    models.County.query
                        .filter_by(name=mandate.county_name)
                        .first())
                if county is None:
                    raise RuntimeError("Can't match county name %r"
                                       % mandate.county_name)
                row['county'] = county

            add_mandate(row)

    if new_people:
        logger.info("%d new people", new_people)

    if no_commit:
        logger.warn("Rolling back the transaction")
        models.db.session.rollback()

    else:
        models.db.session.commit()


@scraper_manager.command
def get_pictures(year='2016'):
    import subprocess
    from sqlalchemy.orm import joinedload

    pictures_dir = Path(flask.current_app.static_folder) / 'pictures' / year

    query = (
        models.Mandate.query
        .filter_by(year=int(year))
        .options(joinedload('person'))
    )

    for mandate in query:
        person = mandate.person
        filename = '%s.jpg' % person.slug
        fs_path = pictures_dir / filename

        if fs_path.exists():
            continue

        if mandate.picture_url is None:
            logger.warn("No picure available for %r", person.name_first_last)
            continue
        assert mandate.picture_url.lower().endswith('.jpg')

        logger.info("Downloading %r" % filename)

        with temp_dir() as tmp:
            tmp = Path(str(tmp))
            orig_path = tmp / 'orig.jpg'
            thumb_path = tmp / 'thumb.jpg'

            resp = requests.get(mandate.picture_url, stream=True)
            assert resp.status_code == 200
            assert resp.headers['Content-Type'] == 'image/jpeg'

            try:
                with orig_path.open('wb') as f:
                    for chunk in resp.iter_content(65536):
                        f.write(chunk)
            finally:
                resp.close()

            logger.info("Converting to thumbnail")
            subprocess.check_call([
                'convert',
                str(orig_path),
                '-geometry', '300x300^',
                '-quality', '85',
                str(thumb_path),
            ])

            logger.info("Uploading to gdrive")

            thumb_path.rename(fs_path)
            logger.info("Got photo: %r", filename)


@scraper_manager.command
def authorize_gdrive():
    from mptracker.scraper import gdrive
    gdrive.authorize()


@scraper_manager.command
def get_groups(
        cache_name=None,
        throttle=None,
        no_commit=False,
        year='2016',
        ):
    year = int(year)

    from mptracker.scraper.groups import GroupScraper, Interval

    http_session = create_session(cache_name=cache_name or
                                       _get_config_cache_name(),
                                  throttle=throttle and float(throttle))
    group_scraper = GroupScraper(http_session)

    mandate_lookup = models.MandateLookup()
    mandate_intervals = defaultdict(list)
    term_interval = TERM_INTERVAL[year]

    groups = list(group_scraper.fetch(year))
    independents = None
    if groups[0].is_independent:
        independents = groups[0]
        groups = groups[1:] + [independents]

    for group in groups:
        for member in group.current_members + group.former_members:
            (myear, chamber, number) = member.mp_ident
            assert chamber == 2
            mandate = mandate_lookup.find(member.mp_name, myear, number)
            interval_list = mandate_intervals[mandate]

            interval = member.get_interval()
            if interval.start is None:
                interval = interval._replace(start=term_interval.lower)

            if interval.end is None:
                interval = interval._replace(end=term_interval.upper)

            if group.is_independent:
                if interval_list:
                    start = interval_list[-1].end
                    interval = interval._replace(start=start)

            interval_list.append(interval)
            interval_list.sort(key=lambda i: i[0])

    for mandate, interval_list in mandate_intervals.items():
        # make sure interval_list are continuous
        new_intervals = []
        for interval_one, interval_two in \
            zip(interval_list[:-1], interval_list[1:]):

            assert interval_one.start < interval_one.end
            if interval_one.end < interval_two.start:
                assert independents is not None
                interval = Interval(
                    start=interval_one.end,
                    end=interval_two.start,
                    group=independents,
                )
                new_intervals.append(interval)
            elif interval_one.end > interval_two.start:
                raise RuntimeError("Overlapping intervals")

        interval_list.extend(new_intervals)
        interval_list.sort()

        mandate_end = mandate.interval.upper
        if mandate_end == date.max:
            mandate_end = None
        if interval_list[-1].end != mandate_end:
            logger.warn("Mandate %s ends at %s",
                        mandate, interval_list[-1].end)

    group_patcher = TablePatcher(
        models.MpGroup,
        models.db.session,
        key_columns=['short_name', 'year'],
        filter={'year': year},
    )

    with group_patcher.process() as add_group:
        for group in groups:
            record = group.as_dict(['name', 'short_name', 'year'])
            group.row = add_group(record).row

        models.db.session.flush()

    membership_patcher = TablePatcher(
        models.MpGroupMembership,
        models.db.session,
        key_columns=['mandate_id', 'mp_group_id', 'interval'],
    )

    current_membership_query = (
        models.db.session.query(models.MpGroupMembership.id)
        .join(models.MpGroupMembership.mandate)
        .filter_by(year=year)
    )

    remove_membership_ids = set(row.id for row in current_membership_query)
    with membership_patcher.process(autoflush=1000) as add_membership:
        for mandate, interval_list in mandate_intervals.items():
            for interval in interval_list:
                res = add_membership({
                    'mandate_id': mandate.id,
                    'mp_group_id': interval.group.row.id,
                    'interval': DateRange(
                        interval.start or date.min,
                        interval.end or date.max,
                    ),
                })
                if not res.is_new:
                    remove_membership_ids.remove(res.row.id)

    if remove_membership_ids:
        unseen_items = (
            models.MpGroupMembership.query
            .filter(models.MpGroupMembership.id.in_(remove_membership_ids))
        )
        unseen_items.delete(synchronize_session=False)
        logger.info("Deleted %d stale memberships", len(remove_membership_ids))

    if no_commit:
        logger.warn("Rolling back the transaction")
        models.db.session.rollback()

    else:
        models.db.session.commit()


@scraper_manager.command
def get_committees(
    cache_name=None,
    throttle=None,
    no_commit=False,
):
    from mptracker.scraper.committees import CommitteeScraper

    mandate_lookup = models.MandateLookup()

    http_session = create_session(
        cache_name=cache_name or _get_config_cache_name(),
        throttle=throttle and float(throttle),
    )

    scraper = CommitteeScraper(http_session)

    committee_patcher = TablePatcher(
        models.MpCommittee,
        models.db.session,
        key_columns=['chamber_id', 'cdep_id'],
    )

    membership_patcher = TablePatcher(
        models.MpCommitteeMembership,
        models.db.session,
        key_columns=['mandate_id', 'mp_committee_id', 'interval'],
    )

    with committee_patcher.process(remove=True) as add_committee, \
         membership_patcher.process(remove=True) as add_membership:
        for committee in scraper.fetch_committees():
            res = add_committee(
                committee.as_dict(['chamber_id', 'cdep_id', 'name']),
            )
            if res.is_new:
                models.db.session.flush()
            mp_committee = res.row

            for member in committee.current_members + committee.former_members:
                if member.end_date and member.end_date < TERM_2016_START:
                    logger.warn(
                        "Membership end date is before the 2016 "
                        "term started, skipping: %r %r %r",
                        member.mp_name, committee.name, member.end_date,
                    )
                    continue
                interval = DateRange(
                    member.start_date or TERM_2016_START,
                    member.end_date or date.max,
                )
                mandate = mandate_lookup.find(
                    member.mp_name,
                    member.mp_ident.year,
                    member.mp_ident.number,
                )
                add_membership({
                    'role': member.role,
                    'interval': interval,
                    'mandate_id': mandate.id,
                    'mp_committee_id': mp_committee.id,
                })

    if no_commit:
        logger.warn("Rolling back the transaction")
        models.db.session.rollback()

    else:
        models.db.session.commit()


@scraper_manager.command
def committee_summaries(year=2016):
    from mptracker.scraper.committee_summaries import SummaryScraper

    patcher = TablePatcher(models.CommitteeSummary,
                           models.db.session,
                           key_columns=['pdf_url'])

    summary_scraper = SummaryScraper(get_cached_session(),
                                     get_cached_session('question-pdf'))
    records = summary_scraper.fetch_summaries(year, get_pdf_text=True)

    patcher.update(records)

    models.db.session.commit()


@scraper_manager.command
def get_proposal_pages(
        throttle=None,
        cache_name=None,
        year=None,
        ):
    from itertools import chain
    from mptracker.scraper.proposals import ProposalScraper

    session = create_session(
        cache_name=cache_name or _get_config_cache_name(),
        throttle=float(throttle) if throttle else None,
    )
    scraper = ProposalScraper(session)

    db_page_date = {
        (chamber, pk): date
        for (chamber, pk, date) in models.db.session.query(
            models.ScrapedProposalPage.chamber,
            models.ScrapedProposalPage.pk,
            models.ScrapedProposalPage.date,
        )
    }

    for record in chain(scraper.list_proposals(2, year),
                        scraper.list_proposals(1, year)):

        old_date = db_page_date.get((record['chamber'], record['pk']))
        if old_date and old_date >= record['date']:
            continue

        if record['chamber'] == 1 and record['pk'] in [18541, 18789, 19110]:
            continue

        get_proposal_single_page(record['chamber'], record['pk'], cache_name)


@scraper_manager.command
def get_proposal_single_page(
        chamber,
        pk,
        cache_name=None,
    ):
    import pickle
    from mptracker.scraper.proposals import ProposalScraper

    session = create_session(cache_name=cache_name or _get_config_cache_name())
    scraper = ProposalScraper(session)

    pk = int(pk)
    chamber = int(chamber)

    record = {
        'pk': pk,
        'chamber': chamber,
        'date': date.today(),
    }

    old_rows = (
        models.ScrapedProposalPage.query
        .filter_by(chamber=chamber, pk=pk)
    )
    old_rows.delete()

    logger.info("scraping %d %d", chamber, pk)
    result = scraper.scrape_proposal_page(chamber, pk)

    scraped_page = models.ScrapedProposalPage(**record)
    scraped_page.result = pickle.dumps(result)
    models.db.session.add(scraped_page)

    models.db.session.commit()


@scraper_manager.command
def get_proposals(
        autoanalyze=False,
        no_commit=False,
        limit=None,
        ):
    import pickle
    from mptracker.scraper.proposals import SingleProposalScraper
    from mptracker.proposals import ocr_proposal
    from mptracker.policy import calculate_proposal

    index = {'pk_cdep': {}, 'pk_senate': {}}

    for p in models.Proposal.query:
        if p.cdeppk_cdep:
            index['pk_cdep'][p.cdeppk_cdep] = p
        if p.cdeppk_senate:
            index['pk_senate'][p.cdeppk_senate] = p

    dirty_proposal_set = set()
    models.db.session.flush()

    for page in models.ScrapedProposalPage.query.filter_by(parsed=False):
        result = pickle.loads(page.result)
        pk_cdep = result.get('pk_cdep')
        pk_senate = result.get('pk_senate')

        if pk_cdep in [15781]:
            continue

        if pk_cdep and pk_cdep in index['pk_cdep']:
            p = index['pk_cdep'][pk_cdep]

            if pk_senate and pk_senate in index['pk_senate']:
                senate_proposal = index['pk_senate'][pk_senate]
                if senate_proposal != p:
                    logger.warn("Deleting stale senate proposal %r",
                                senate_proposal.id)
                    senate_proposal.sponsorships.delete()
                    models.db.session.delete(senate_proposal)
                    models.db.session.flush()

        elif pk_senate and pk_senate in index['pk_senate']:
            p = index['pk_senate'][pk_senate]

        else:
            p = models.Proposal()

        if p.cdeppk_cdep:
            if pk_cdep != p.cdeppk_cdep:
                if page.chamber == 1:
                    p.cdeppk_cdep = pk_cdep

                elif page.chamber == 2 and pk_senate:
                    senate_page = (
                        models.ScrapedProposalPage.query
                        .filter_by(chamber=1, pk=pk_senate)
                        .one()
                    )
                    pk_cdep = pickle.loads(senate_page.result).get('pk_cdep')
                    if pk_cdep and pk_cdep != page.pk:
                        page.parsed = True
                    p.cdeppk_cdep = pk_cdep

                else:
                    raise RuntimeError(repr((pk_cdep, p.cdeppk_cdep, p.id)))
        elif pk_cdep:
            p.cdeppk_cdep = pk_cdep
            index['pk_cdep'][pk_cdep] = p

        if p.cdeppk_senate:
            if not (pk_senate is None or pk_senate == p.cdeppk_senate):
                # warning: page.id, pk_senate, p.cdeppk_senate, p.id
                continue
        elif pk_senate:
            p.cdeppk_senate = pk_senate
            index['pk_senate'][pk_senate] = p

        dirty_proposal_set.add(p)

        if limit and len(dirty_proposal_set) >= int(limit):
            break

    models.db.session.flush()


    def cdep_id(mandate):
        return (mandate.year, mandate.cdep_number)

    by_cdep_id = {cdep_id(m): m for m in models.Mandate.query}

    chamber_by_slug = {c.slug: c for c in models.Chamber.query}

    proposal_patcher = TablePatcher(models.Proposal,
                                    models.db.session,
                                    key_columns=['id'])

    sp_updates = sp_added = sp_removed = 0

    changed = []
    seen = []

    with proposal_patcher.process(autoflush=1000) as add_proposal:
        for proposal in dirty_proposal_set:
            page_cdep = (
                models.ScrapedProposalPage.query
                .filter_by(chamber=2, pk=proposal.cdeppk_cdep)
                .first()
            )
            page_senate = (
                models.ScrapedProposalPage.query
                .filter_by(chamber=1, pk=proposal.cdeppk_senate)
                .first()
            )

            single_scraper = SingleProposalScraper()

            if page_senate:
                single_scraper.scrape_page('senate',
                    pickle.loads(page_senate.result))
                page_senate.parsed = True

            if page_cdep:
                single_scraper.scrape_page('cdep',
                    pickle.loads(page_cdep.result))
                page_cdep.parsed = True

            prop = single_scraper.finalize()

            prop.id = proposal.id or models.random_uuid()
            prop.cdeppk_cdep = proposal.cdeppk_cdep
            prop.cdeppk_senate = proposal.cdeppk_senate


            record = prop.as_dict(['id', 'cdeppk_cdep', 'cdeppk_senate',
                'decision_chamber', 'url', 'title', 'date', 'number_bpi',
                'number_cdep', 'number_senate', 'proposal_type',
                'pdf_url', 'status', 'status_text', 'modification_date'])

            record['activity'] = flask.json.dumps([
                item.as_dict(['date', 'location', 'html'])
                for item in prop.activity
            ])

            slug = prop.decision_chamber
            if slug:
                record['decision_chamber'] = chamber_by_slug[slug]

            if record['cdeppk_cdep'] == 15484 and record['cdeppk_senate'] == 19552:
                record['cdeppk_senate'] = None
            result = add_proposal(record)
            row = result.row
            if result.is_changed:
                changed.append(row)
            seen.append(row)

            new_people = set(by_cdep_id[ci] for ci in prop.sponsorships)
            existing_sponsorships = {sp.mandate: sp
                                     for sp in row.sponsorships}
            to_remove = set(existing_sponsorships) - set(new_people)
            to_add = set(new_people) - set(existing_sponsorships)
            if to_remove:
                logger.info("Removing sponsors %s: %r", row.id,
                            [cdep_id(m) for m in to_remove])
                sp_removed += 1
                for m in to_remove:
                    sp = existing_sponsorships[m]
                    models.db.session.delete(sp)
            if to_add:
                logger.info("Adding sponsors %s: %r", row.id,
                            [cdep_id(m) for m in to_add])
                sp_added += 1
                for m in to_add:
                    row.sponsorships.append(models.Sponsorship(mandate=m))

            if to_remove or to_add:
                sp_updates += 1


    if no_commit:
        logger.warn("Rolling back the transaction")
        models.db.session.rollback()
        return

    models.db.session.commit()

    logger.info("Updated sponsorship for %d proposals (+%d, -%d)",
                sp_updates, sp_added, sp_removed)

    if autoanalyze:
        logger.info("Scheduling analysis jobs for %d proposals", len(changed))
        for proposal in changed:
            if proposal.pdf_url:
                ocr_proposal.delay(proposal.id, autoanalyze=True)

        logger.info("Scheduling policy jobs for %d proposals", len(seen))
        for proposal in seen:
            if proposal.policy_domain_id is None:
                calculate_proposal.delay(proposal.id)


@scraper_manager.command
def get_transcripts(start=None, n_sessions=1, cache_name=None, throttle=None):
    from mptracker.scraper.transcripts import TranscriptScraper

    if start is None:
        max_serial = models.db.session.execute(
            'select serial from transcript_chapter '
            'order by serial desc limit 1').scalar()
        start = int(max_serial.split('/')[0]) + 1

    cdeppk = int(start) - 1
    n_sessions = int(n_sessions)

    transcript_scraper = TranscriptScraper(
            session=create_session(cache_name=cache_name or
                                               _get_config_cache_name(),
                                   throttle=throttle and float(throttle)))

    mandate_lookup = models.MandateLookup()

    transcript_patcher = TablePatcher(models.Transcript,
                                      models.db.session,
                                      key_columns=['serial'])

    with transcript_patcher.process() as add:
        while n_sessions > 0:
            n_sessions -= 1
            cdeppk += 1
            logger.info("Fetching session %s", cdeppk)
            session_data = transcript_scraper.fetch_session(cdeppk)
            if session_data is None:
                logger.info("No content")
                continue
            for chapter in session_data.chapters:
                chapter_row = (models.TranscriptChapter.query
                                        .filter_by(serial=chapter.serial)
                                        .first())
                if chapter_row is None:
                    chapter_row = models.TranscriptChapter(
                        serial=chapter.serial)
                    models.db.session.add(chapter_row)
                    models.db.session.flush()

                chapter_row.date = session_data.date
                chapter_row.headline = chapter.headline

                for paragraph in chapter.paragraphs:
                    if paragraph['mandate_chamber'] != 2:
                        continue
                    try:
                        mandate = mandate_lookup.find(
                                paragraph['speaker_name'],
                                paragraph['mandate_year'],
                                paragraph['mandate_number'])
                    except models.LookupError as e:
                        logger.warn("at %s %s", paragraph['serial'], e)
                        continue

                    transcript_data = {
                        'chapter_id': chapter_row.id,
                        'text': paragraph['text'],
                        'serial': paragraph['serial'],
                        'mandate_id': mandate.id,
                    }
                    add(transcript_data)

    models.db.session.commit()


@scraper_manager.command
def import_person_xls(xls_path):
    """ Import persons, committees and groups from a csv.
    """
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

    models.db.session.commit()


@scraper_manager.command
def get_votes(
        start=None,
        days=1,
        cache_name=None,
        throttle=None,
        no_commit=False,
        autoanalyze=False,
        ):
    from mptracker.scraper.votes import VoteScraper

    if start is None:
        start = models.db.session.execute(
            'select date from voting_session '
            'order by date desc limit 1').scalar() + ONE_DAY

    else:
        start = parse_date(start)

    days = int(days)

    http_session = create_session(cache_name=cache_name or
                                       _get_config_cache_name(),
                                  throttle=throttle and float(throttle))
    vote_scraper = VoteScraper(http_session)


    voting_session_patcher = TablePatcher(
        models.VotingSession,
        models.db.session,
        key_columns=['cdeppk'],
    )

    vote_patcher = TablePatcher(
        models.Vote,
        models.db.session,
        key_columns=['voting_session_id', 'mandate_id'],
    )

    proposal_ids = {p.cdeppk_cdep: p.id for p in models.Proposal.query}
    mandate_lookup = models.MandateLookup()

    new_voting_session_list = []

    with voting_session_patcher.process() as add_voting_session:
        with vote_patcher.process() as add_vote:
            the_date = start
            while days > 0 and the_date < date.today():
                logger.info("Scraping votes from %s", the_date)

                today_has_votes = False
                for voting_session in vote_scraper.scrape_day(the_date):
                    today_has_votes = True
                    record = model_to_dict(
                        voting_session,
                        ['cdeppk', 'subject', 'subject_html'],
                    )
                    record['date'] = the_date
                    proposal_cdeppk = voting_session.proposal_cdeppk
                    record['proposal_id'] = (proposal_ids.get(proposal_cdeppk)
                                             if proposal_cdeppk else None)
                    record['final'] = bool("vot final" in
                                           record['subject'].lower())
                    vs = add_voting_session(record).row
                    if vs.id is None:
                        models.db.session.flush()

                    new_voting_session_list.append(vs.id)

                    for vote in voting_session.votes:
                        record = model_to_dict(vote, ['choice'])
                        record['voting_session_id'] = vs.id
                        mandate = mandate_lookup.find(
                            vote.mandate_name,
                            vote.mandate_year,
                            vote.mandate_number,
                        )
                        record['mandate_id'] = mandate.id
                        add_vote(record)

                if today_has_votes:
                    days -= 1

                the_date += ONE_DAY

    if no_commit:
        logger.warn("Rolling back the transaction")
        models.db.session.rollback()

    else:
        models.db.session.commit()

    if autoanalyze:
        from mptracker.votes import calculate_voting_session_loyalty
        logger.info("Scheduling %d jobs", len(new_voting_session_list))
        for voting_session_id in new_voting_session_list:
            calculate_voting_session_loyalty.delay(voting_session_id)


@scraper_manager.command
def get_vote_controversy(no_commit=False):
    controversy_patcher = TablePatcher(
        models.VotingSessionControversy,
        models.db.session,
        key_columns=['voting_session_id'],
    )

    with controversy_patcher.process(remove=True) as add_controversy:
        for line in get_gdrive_csv(CONTROVERSY_CSV_KEY):
            add_controversy({
                'title': line['title'],
                'status': line['status'],
                'reason': line['motive'],
                'vote_meaning_yes': line['info_da'],
                'vote_meaning_no': line['info_nu'],
                'press_links': line['link_presa'],
                'voting_session_id': line['mptracker_url'].split('/votes/')[1],
            })

    if no_commit:
        logger.warn("Rolling back the transaction")
        models.db.session.rollback()

    else:
        models.db.session.commit()


@scraper_manager.command
def get_position(no_commit=False):
    name_search = models.NameSearch(
        models.Person.query
        .join(models.Mandate)
        .filter(models.Mandate.year == 2016)
        .all()
    )

    position_patcher = TablePatcher(
        models.Position,
        models.db.session,
        key_columns=['person_id', 'interval', 'title'],
    )

    def cabinet_position_row_iter():
        yield from get_gdrive_csv(POSITION_PONTA2_CSV_KEY)
        yield from get_gdrive_csv(POSITION_PONTA3_CSV_KEY)

    with position_patcher.process(remove=True) as add_position:
        for row in cabinet_position_row_iter():
            if row['temporary'].strip():
                continue

            name = row['name'].strip()
            matches = name_search.find(name)

            if len(matches) == 1:
                [person] = matches
                interval = parse_interval(row['start_date'], row['end_date'])
                add_position({
                    'person_id': person.id,
                    'interval': interval,
                    'title': row['title'],
                    'url': row['url'] or None,
                    'category': 'minister',
                })

            elif len(matches) > 1:
                logger.warn("Multiple matches for %r", name)

            else:
                logger.warn("No matches for %r", name)

        for row in get_gdrive_csv(POSITION_BIROU_CDEP_CSV_KEY):
            name = row['name'].strip()
            matches = name_search.find(name)

            assert len(matches) == 1, \
                "Expected a single match for %r, got %r" % (name, matches)

            [person] = matches
            add_position({
                'person_id': person.id,
                'interval': parse_interval(row['start_date'], row['end_date']),
                'title': row['title'] + ", Biroul Permanent",
                'category': 'permanent-bureau',
            })

    if no_commit:
        logger.warn("Rolling back the transaction")
        models.db.session.rollback()

    else:
        models.db.session.commit()


@scraper_manager.command
def get_cabinet_party():
    patcher = TablePatcher(
        models.CabinetMembership,
        models.db.session,
        key_columns=['mp_group_id', 'interval'],
    )

    group_by_code = {g.short_name: g for g in models.MpGroup.query}

    with patcher.process(remove=True) as add_membership:
        for row in get_gdrive_csv(CABINET_PARTY_CSV_KEY):
            if row['legislature'] == '2016':
                group = group_by_code[row['code']]
                interval = parse_interval(row['start_date'], row['end_date'])
                add_membership({
                    'mp_group_id': group.id,
                    'interval': interval,
                })

    models.db.session.commit()


@scraper_manager.command
def get_policy_domain():
    patcher = TablePatcher(
        models.PolicyDomain,
        models.db.session,
        key_columns=['slug'],
    )

    with patcher.process(remove=True) as add_policy_domain:
        for row in get_gdrive_csv(POLICY_DOMAIN_CSV_KEY):
            add_policy_domain(row)

    models.db.session.commit()


@scraper_manager.command
def get_stop_words():
    from mptracker.nlp import normalize_to_ascii
    patcher = TablePatcher(
        models.Stopword,
        models.db.session,
        key_columns=['id'],
    )

    with patcher.process(remove=True) as add_stop_word:
        for row in get_gdrive_csv(STOP_WORDS_CSV_KEY):
            add_stop_word({'id': normalize_to_ascii(row['id'])})

    models.db.session.commit()


@scraper_manager.command
def get_committee_attendance(no_commit=False):
    # Nume
    # Comisia Permanenta 1
    # Numar sedinte comisia permanenta 1
    # Numar prezente deputat la sedintele comisiei 1 in 2013
    # Comisia Permanenta 2
    # Numar sedinte comisia permanenta 2
    # Numar prezente deputat la sedintele comisiei 2 in 2013
    # Comisia Speciala
    # Numar sedinte comisia speciala
    # Numar prezente deputat la sedintele comisiei speciale in 2013

    person_map = {
        p.name: p
        for p in (
            models.Person.query
            .join(models.Person.mandates)
            .filter_by(year=2016)
        )
    }

    committee_map = {
        re.sub(r'\s+', ' ', c.name): c
        for c in (
            models.MpCommittee.query
            .filter(models.MpCommittee.chamber_id.in_([0, 2]))
        )
    }

    def parse_committee_data(row, number):
        name = row['Comisia Permanenta %d' % number].strip()
        name = re.sub(r'\s+', ' ', name)
        if name in ['', '0']:
            return None

        if 'Subcomisia pentru' in name:
            logger.warn("Skipping committee %r", name)
            return None

        if name not in committee_map:
            logger.warn("Skipping membership %r %r", row['Nume'], name)
            return None

        committee = committee_map[name]

        meetings_2013_txt = row['Numar sedinte comisia permanenta %d' % number]
        attended_2013_txt = row['Numar prezente deputat la sedintele '
                                'comisiei %d in 2013' % number]

        try:
            meetings_2013 = int(meetings_2013_txt)
            attended_2013 = int(attended_2013_txt)

        except ValueError:
            #logger.warn("Skipping numbers: %r %r",
            #            meetings_2013_txt, attended_2013_txt)
            return None

        if meetings_2013 == 0:
            return None

        attendance_2013 = attended_2013 / meetings_2013
        return (committee, attendance_2013)

    for row in get_gdrive_csv(COMMITTEE_ROLL_CALL_CSV_KEY):
        person = person_map[row['Nume'].strip()]
        mandate = (
            person.mandates
            .filter_by(year=2016)
            .order_by('interval')
            .first()
        )

        for n in [1, 2]:
            _data = parse_committee_data(row, n)
            if _data is None:
                continue

            (committee, attendance_2013) = _data
            membership = (
                committee.memberships
                .filter_by(mandate=mandate)
                .order_by('interval')
                .first()
            )

            if membership.attendance_2013 is not None:
                if not almost_eq(membership.attendance_2013, attendance_2013):
                    logger.warn(
                        "Updating attendance: %r %r -> %r",
                        person.name,
                        membership.attendance_2013,
                        attendance_2013,
                    )
            membership.attendance_2013 = attendance_2013

    if no_commit:
        logger.warn("Rolling back the transaction")
        models.db.session.rollback()

    else:
        models.db.session.commit()


@scraper_manager.command
def get_romania_curata():
    from os import path
    from difflib import SequenceMatcher as sm
    from itertools import permutations
    import json
    from mptracker.nlp import normalize

    sql_names = [person.name for person in models.Person.query.all()]

    with open(path.relpath("mptracker/scraper/scraper_curata_out.json"),
              'r', encoding='utf-8') as f:
        scraper_result = json.load(f)

    with open(path.relpath(
            'mptracker/scraper/romania_curata_exceptions.json'),
            'r', encoding='utf-8') as f:
        person_exceptions = json.load(f)


    def matching_score(first_name, second_name):
        return sm(None, first_name, second_name).ratio() * 100

    def add_person(name, fortune):
        person = (
            models.Person.query
                .filter_by(name=name)
                .first()
        )
        if person != None:
            person.romania_curata = "\n".join(fortune)
            print("Found a match for ", name.encode('utf-8'))
            sql_names.remove(name)

    for name, fortune in scraper_result:
        name_scraper = normalize(name)
        max_matching = (0, 0)

        if name_scraper in person_exceptions:
            add_person(person_exceptions[name_scraper], fortune)

        for temporary_sqlname in sql_names:
            name_sql = normalize(temporary_sqlname)
            for perm in permutations(name_scraper.split(" ")):
                current_matching = matching_score(" ".join(perm), name_sql)

                if max_matching[0] < current_matching:
                    max_matching = (current_matching, temporary_sqlname)

        if max_matching[0] > 93:
            add_person(max_matching[1], fortune)

    models.db.session.commit()


@scraper_manager.command
def assets(file_path, no_commit=False):
    from mptracker.scraper.assets import parse_assets
    from mptracker.nlp import normalize

    asset_patcher = TablePatcher(
        models.AssetStatement,
        models.db.session,
        key_columns=['person_id', 'date'],
    )

    people_map = {
        normalize(person.name): person.id
        for person in (
            models.Person.query
            .join(models.Person.mandates)
            .filter_by(year=2016)
        )
    }

    with asset_patcher.process(remove=True) as add_asset:
        for record in parse_assets(file_path):
            person_name = normalize(record.pop('person_name'))
            person_id = people_map[person_name]
            del record['constituency']
            del record['county']
            res = add_asset({
                'person_id': person_id,
                'date': date(2016, 11, 1),
                'raw_data': record,
                'net_worth_eur': (
                    record['acct_value']['TOTAL_EUR']
                    - record['debt_value']['TOTAL_EUR']
                    + record['invest_value']['TOTAL_EUR']
                    + record['valuables_value']['TOTAL_EUR']
                ),
                'land_agri_area': record['land_agri_area'],
                'land_city_area': record['land_city_area'],
                'realty_count': (
                    record['realty_apartment_count'] +
                    record['realty_business_count'] +
                    record['realty_house_count']
                ),
                'vehicle_count': record['vehicle_count'],
                'year_income_eur': (
                    record['family_income_value']['TOTAL_EUR'] +
                    record['gift_value']['TOTAL_EUR'] +
                    record['sales_value']['TOTAL_EUR']
                ),
            })

    if no_commit:
        logger.warn("Rolling back the transaction")
        models.db.session.rollback()

    else:
        models.db.session.commit()



@scraper_manager.command
def daily():
    with log_to_sentry():
        get_transcripts(n_sessions=20)
        get_questions(autoanalyze=True)
        get_votes(days=20, autoanalyze=True)
        get_groups()
        get_proposal_pages()
        get_proposals(autoanalyze=True)


@scraper_manager.command
def daily_long():
    with log_to_sentry():
        get_people()
        get_committees()


@scraper_manager.command
def daily_gdrive():
    with log_to_sentry():
        get_vote_controversy()
        get_position()
        get_cabinet_party()
        get_policy_domain()
        get_stop_words()
        #get_committee_attendance()
        get_proposal_controversy()
        get_member_count()
        get_committee_policy()


@scraper_manager.command
def update_person_xls():
    """ Update person contact data from csv"""
    from mptracker.scraper.person_xls import read_person_contact

    mandate_lookup = models.MandateLookup()

    people_data = []
    mandate_patcher = TablePatcher(models.Mandate,
                                   models.db.session,
                                   key_columns=['year', 'cdep_number'])
    with mandate_patcher.process() as add:
        for record in read_person_contact(MINORITIES_CSV_KEY):
            mandate = mandate_lookup.find(record.pop('name'), record['year'],
                                          record['cdep_number'])
            person_data = record.pop('person_data')
            person_data['id'] = mandate.person_id
            people_data.append(person_data)
            add(record)

    person_patcher = TablePatcher(models.Person,
                                  models.db.session,
                                  key_columns=['id'])
    with person_patcher.process() as add:
        for person_data in people_data:
            add(person_data)

    models.db.session.commit()


@scraper_manager.command
def get_proposal_controversy():
    """ Update proposal controversies from csv"""

    def extract_proposal(url):
        return url[url.rfind('/') + 1:]

    controversy_patcher = TablePatcher(models.ProposalControversy,
                                       models.db.session,
                                       key_columns=['proposal_id'])
    with controversy_patcher.process(remove=True) as add:
        for row in get_gdrive_csv(PROPOSAL_CONTROVERSY_CSV_KEY):
            proposal_id = extract_proposal(row['Link MP Tracker'])
            if not proposal_id:
                continue
            assert models.Proposal.query.get(proposal_id)

            record = {
                'proposal_id': proposal_id,
                'title': row['Titlu'],
                'reason': row['Motive controversa'],
                'press_links': row['Link presa'],
            }
            add(record)

    models.db.session.commit()


@scraper_manager.command
def get_member_count():
    patcher = TablePatcher(
        models.MemberCount,
        models.db.session,
        key_columns=['short_name', 'year'],
    )

    with patcher.process(remove=True) as add_member_count:
        for row in get_gdrive_csv(MEMBER_COUNT_CSV_KEY):
            short_name = row.pop('')
            for year, count in row.items():
                add_member_count({
                    'short_name': short_name,
                    'year': int(year),
                    'count': int(count),
                })

    models.db.session.commit()


@scraper_manager.command
def get_committee_policy():
    patcher = TablePatcher(
        models.MpCommittee,
        models.db.session,
        key_columns=['id'],
    )

    with patcher.process() as update_committee:
        for row in get_gdrive_csv(COMMITTEE_POLICY_CSV_KEY):
            slug = row['policy']

            policy_id = None
            if slug:
                policy = models.PolicyDomain.query.filter_by(slug=slug).first()
                if policy is None:
                    logger.warn("Unknown policy domain %r", slug)
                else:
                    policy_id = policy.id

            update_committee(
                dict(id=row['id'], policy_domain_id=policy_id),
                create=False
            )

    models.db.session.commit()
