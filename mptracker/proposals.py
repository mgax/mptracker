from time import sleep
import logging
import flask
from flask.ext.script import Manager
from flask.ext.rq import job
from mptracker import models
from mptracker.common import ocr_url
from mptracker.nlp import match_text_for_person

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

proposals = flask.Blueprint('proposals', __name__)

proposals_manager = Manager()


@proposals.route('/mandate/<uuid:mandate_id>/proposals')
def mandate_proposals(mandate_id):
    mandate = models.Mandate.query.get_or_404(mandate_id)
    return flask.render_template('proposals/mandate.html', **{
        'mandate': mandate,
        'sponsorships': list(mandate.sponsorships),
    })


@proposals.route('/proposals/<uuid:proposal_id>')
def proposal(proposal_id):
    proposal = (models.Proposal.query
                    .filter_by(id=proposal_id)
                    .first_or_404())
    return flask.render_template('proposals/detail.html', **{
        'proposal': proposal,
        'sponsorships': [{
                'mandate': sp.mandate,
                'match_data': flask.json.loads(sp.match.data or '{}'),
            } for sp in proposal.sponsorships],
    })


@proposals.route('/proposals/relevant')
def relevant():
    sponsorships = [s for s in models.Sponsorship.query if s.match.score]
    sponsorships.sort(key=lambda s: s.match.score or 0, reverse=True)
    return flask.render_template('proposals/relevant.html', **{
        'sponsorships': sponsorships,
    })


@proposals_manager.command
def ocr_all(number=None, force=False):
    job_map = {}

    n_jobs = n_skip = n_ok = 0
    for proposal in models.Proposal.query:
        if not proposal.pdf_url:
            n_skip += 1
            continue
        if proposal.text is not None and not force:
            n_ok += 1
            continue

        job = ocr_url.delay(proposal.pdf_url)
        job_map[proposal.id] = job

        n_jobs += 1
        if number and n_jobs >= int(number):
            break
    logger.info("enqueued %d jobs, skipped %d, ok %d", n_jobs, n_skip, n_ok)

    session = models.db.session

    while job_map:
        sleep(1)

        done = set()
        failed = set()
        session.rollback()
        for proposal_id, job in job_map.items():
            if job.is_finished:
                done.add(proposal_id)
                proposal = models.Proposal.query.get(proposal_id)
                pages = job.result
                proposal.text = '\n\n'.join(pages)

            elif job.is_failed:
                failed.add(proposal_id)

        session.commit()

        if done or failed:
            for proposal_id in done | failed:
                del job_map[proposal_id]
            logger.info("saved %d, failed %d, remaining %d",
                        len(done), len(failed), len(job_map))


@job
@proposals_manager.command
def analyze_sponsorship(sponsorship_id):
    sponsorship = models.Sponsorship.query.get(sponsorship_id)
    proposal = sponsorship.proposal
    text = proposal.title + ' ' + proposal.text
    result = match_text_for_person(sponsorship.person, text)
    sponsorship.match.data = flask.json.dumps(result)
    sponsorship.match.score = len(result['top_matches'])
    models.db.session.commit()


@proposals_manager.command
def analyze_all(number=None, force=False, minority_only=False):
    n_jobs = n_skip = n_ok = 0
    for sponsorship in models.Sponsorship.query:
        if not force:
            if sponsorship.match.data is not None:
                n_ok += 1
                continue
        if sponsorship.proposal.text is None:
            n_skip += 1
            continue
        if not sponsorship.person.minority:
            county = sponsorship.person.county
            if (minority_only or
                county is None or
                county.geonames_code is None):
                n_skip += 1
                continue
        analyze_sponsorship.delay(sponsorship.id)
        n_jobs += 1
        if number and n_jobs >= int(number):
            break
    logger.info("enqueued %d jobs, skipped %d, ok %d", n_jobs, n_skip, n_ok)
