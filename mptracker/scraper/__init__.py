import logging
from datetime import timedelta, date
from collections import defaultdict
from flask.ext.script import Manager
from psycopg2.extras import DateRange
from mptracker.scraper.common import get_cached_session, create_session
from mptracker import models
from mptracker.common import parse_date, model_to_dict
from mptracker.patcher import TablePatcher

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

scraper_manager = Manager()

ONE_DAY = timedelta(days=1)

TERM_2012_START = date(2012, 12, 19)


@scraper_manager.command
def questions(
        year='2013',
        reimport_existing=False,
        cache_name=None,
        throttle=None,
        autoanalyze=False,
        ):
    from mptracker.scraper.questions import QuestionScraper
    from mptracker.questions import ocr_question
    from mptracker.policy import calculate_question

    if reimport_existing:
        known_urls = set()
    else:
        known_urls = set(q.url for q in models.Question.query)

    def skip_question(url):
        return url in known_urls

    http_session = create_session(cache_name=cache_name,
                                  throttle=throttle and float(throttle),
                                  counters=True)
    questions_scraper = QuestionScraper(session=http_session,
                                        skip=skip_question)

    mandate_lookup = models.MandateLookup()

    question_patcher = TablePatcher(models.Question,
                                    models.db.session,
                                    key_columns=['number', 'date'])

    new_ask_rows = 0

    changed = []

    with question_patcher.process() as add:
        for question in questions_scraper.run(int(year)):
            person_list = question.pop('person')
            question['addressee'] = '; '.join(question['addressee'])
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
                changed.append(q)

            assert not old_asked

    models.db.session.commit()

    if new_ask_rows:
        logger.info("Added %d ask records", new_ask_rows)

    counters = http_session.counters
    logger.info("HTTP: %d kb in %s requests, %.2f seconds",
                counters['bytes'] / 1024, counters['requests'],
                counters['download_time'].total_seconds())

    if autoanalyze:
        logger.info("Scheduling jobs for %d questions", len(changed))
        for question in changed:
            if question.pdf_url:
                ocr_question.delay(question.id, autoanalyze=True)

            if question.policy_domain_id is None:
                calculate_question.delay(question.id)


@scraper_manager.command
def people(
    year='2012',
    cache_name=None,
    throttle=None,
    no_commit=False,
):
    from mptracker.scraper.people import MandateScraper

    http_session = create_session(
        cache_name=cache_name,
        throttle=throttle and float(throttle),
    )
    mandate_scraper = MandateScraper(http_session)

    mandate_patcher = TablePatcher(
        models.Mandate,
        models.db.session,
        key_columns=['year', 'cdep_number'],
    )

    with mandate_patcher.process() as add_mandate:
        for mandate in mandate_scraper.fetch(year):
            row = mandate.as_dict([
                'year',
                'cdep_number',
                'minority',
                'college',
                'constituency',
                'picture_url',
            ])
            if year == '2012':
                end_date = mandate.end_date or date.max
                row['interval'] = DateRange(TERM_2012_START, end_date)

            person = (
                models.Person.query
                    .filter_by(name=mandate.person_name)
                    .first())
            if person is None:
                raise RuntimeError("Can't find person named %r"
                                   % mandate.person_name)

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

    if no_commit:
        logger.warn("Rolling back the transaction")
        models.db.session.rollback()

    else:
        models.db.session.commit()


@scraper_manager.command
def groups(
        cache_name=None,
        throttle=None,
        no_commit=False,
        ):
    from mptracker.scraper.groups import GroupScraper, Interval

    http_session = create_session(cache_name=cache_name,
                                  throttle=throttle and float(throttle))
    group_scraper = GroupScraper(http_session)

    mandate_lookup = models.MandateLookup()
    mandate_intervals = defaultdict(list)

    groups = list(group_scraper.fetch())
    independents = groups[0]
    assert independents.is_independent
    for group in groups[1:] + [independents]:
        for member in group.current_members + group.former_members:
            (year, chamber, number) = member.mp_ident
            assert chamber == 2
            mandate = mandate_lookup.find(member.mp_name, year, number)
            interval_list = mandate_intervals[mandate]

            interval = member.get_interval()
            if interval.start is None:
                interval = interval._replace(start=TERM_2012_START)

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
        key_columns=['short_name'],
    )

    with group_patcher.process(remove=True) as add_group:
        for group in groups:
            record = group.as_dict(['name', 'short_name'])
            group.row = add_group(record).row

        models.db.session.flush()

    membership_patcher = TablePatcher(
        models.MpGroupMembership,
        models.db.session,
        key_columns=['mandate_id', 'mp_group_id', 'interval'],
    )

    with membership_patcher.process(
            autoflush=1000,
            remove=True,
        ) as add_membership:

        for mandate, interval_list in mandate_intervals.items():
            for interval in interval_list:
                row = add_membership({
                    'mandate_id': mandate.id,
                    'mp_group_id': interval.group.row.id,
                    'interval': DateRange(
                        interval.start or date.min,
                        interval.end or date.max,
                    ),
                }).row

    if no_commit:
        logger.warn("Rolling back the transaction")
        models.db.session.rollback()

    else:
        models.db.session.commit()


@scraper_manager.command
def committees(
    cache_name=None,
    throttle=None,
    no_commit=False,
):
    from mptracker.scraper.committees import CommitteeScraper

    patcher = TablePatcher(
        models.MpCommittee,
        models.db.session,
        key_columns=['chamber_id', 'cdep_id'],
    )

    http_session = create_session(
        cache_name=cache_name,
        throttle=throttle and float(throttle),
    )
    scraper = CommitteeScraper(http_session)
    with patcher.process(autoflush=1000, remove=True) as add:
        for committee in scraper.fetch_committees():
            add(committee.as_dict(['chamber_id', 'cdep_id', 'name']))

    if no_commit:
        logger.warn("Rolling back the transaction")
        models.db.session.rollback()

    else:
        models.db.session.commit()


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

    models.db.session.commit()


@scraper_manager.command
def proposals(
        cache_name=None,
        throttle=None,
        autoanalyze=False,
        ):
    from mptracker.scraper.proposals import ProposalScraper
    from mptracker.proposals import ocr_proposal
    from mptracker.policy import calculate_proposal

    proposal_scraper = ProposalScraper(create_session(
            cache_name=cache_name,
            throttle=float(throttle) if throttle else None))

    def cdep_id(mandate):
        return (mandate.year, mandate.cdep_number)

    by_cdep_id = {cdep_id(m): m
                  for m in models.Mandate.query
                  if m.year == 2012}

    id_cdeppk_cdep = {}
    id_cdeppk_senate = {}
    for proposal in models.Proposal.query:
        if proposal.cdeppk_cdep:
            id_cdeppk_cdep[proposal.cdeppk_cdep] = proposal.id
        if proposal.cdeppk_senate:
            id_cdeppk_senate[proposal.cdeppk_senate] = proposal.id

    chamber_by_slug = {c.slug: c for c in models.Chamber.query}

    proposals = proposal_scraper.fetch_from_mp_pages(set(by_cdep_id.keys()))

    all_activity = defaultdict(list)
    for item in models.ProposalActivityItem.query:
        all_activity[item.proposal_id].append(item)

    proposal_patcher = TablePatcher(models.Proposal,
                                    models.db.session,
                                    key_columns=['id'])

    activity_patcher = TablePatcher(models.ProposalActivityItem,
                                    models.db.session,
                                    key_columns=['id'])

    sp_updates = sp_added = sp_removed = 0

    changed = []
    seen = []

    with proposal_patcher.process(autoflush=1000, remove=True) as add_proposal:
        with activity_patcher.process(autoflush=1000, remove=True) \
                as add_activity:
            for prop in proposals:
                record = model_to_dict(prop, ['cdeppk_cdep', 'cdeppk_senate',
                    'decision_chamber', 'url', 'title', 'date', 'number_bpi',
                    'number_cdep', 'number_senate', 'proposal_type',
                    'pdf_url'])

                slug = prop.decision_chamber
                if slug:
                    record['decision_chamber'] = chamber_by_slug[slug]

                idc = id_cdeppk_cdep.get(prop.cdeppk_cdep)
                ids = id_cdeppk_senate.get(prop.cdeppk_senate)
                if idc and ids and idc != ids:
                    logger.warn("Two different records for the same proposal: "
                                "(%s, %s). Removing the 2nd.", idc, ids)
                    models.db.session.delete(models.Proposal.query.get(ids))
                    ids = None
                record['id'] = idc or ids or models.random_uuid()

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

                db_activity = all_activity[row.id]
                db_activity.sort(key=lambda a: a.order)
                act_fields = lambda r: (r.date, r.location)
                if ([act_fields(r) for r in db_activity] !=
                    [act_fields(r) for r in prop.activity[:len(db_activity)]]):
                    logger.warn("History doesn't match for %s, "
                                "%d items will be removed",
                                row.id,len(db_activity))
                    db_activity = []

                for n, ac in enumerate(prop.activity):
                    record = model_to_dict(ac, ['date', 'location', 'html'])
                    record['proposal_id'] = row.id
                    record['order'] = n
                    if n < len(db_activity):
                        item = db_activity[n]
                        record['id'] = item.id
                        assert item.date == record['date']
                        assert item.location == record['location']
                        assert item.order == record['order']
                    else:
                        record['id'] = models.random_uuid()
                    add_activity(record)

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
def transcripts(start=None, n_sessions=1, cache_name=None, throttle=None):
    from mptracker.scraper.transcripts import TranscriptScraper

    if start is None:
        max_serial = models.db.session.execute(
            'select serial from transcript_chapter '
            'order by serial desc limit 1').scalar()
        start = int(max_serial.split('/')[0]) + 1

    cdeppk = int(start) - 1
    n_sessions = int(n_sessions)

    transcript_scraper = TranscriptScraper(
            session=create_session(cache_name=cache_name,
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
def votes(
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

    http_session = create_session(cache_name=cache_name,
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
            for delta in range(days):
                the_date = start + ONE_DAY * delta
                if the_date >= date.today():
                    # don't scrape today, maybe voting is not done yet!
                    break
                logger.info("Scraping votes from %s", the_date)
                for voting_session in vote_scraper.scrape_day(the_date):
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
def get_romania_curata():
    from os import path
    from difflib import SequenceMatcher as sm
    from itertools import permutations
    import json
    from mptracker.nlp import normalize

    sql_names = [person.name for person in models.Person.query.all()]

    with open(path.relpath("mptracker/placename_data/scraper-curata.json"),
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
