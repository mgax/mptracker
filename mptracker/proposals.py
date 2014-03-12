from time import sleep
import logging
import flask
from flask.ext.script import Manager
from flask.ext.rq import job
from mptracker import models
from mptracker.common import ocr_url
from mptracker.nlp import match_text_for_mandate

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


@proposals.route('/proposals/')
def index():
    return flask.render_template('proposals/index.html', **{
        'proposals': iter(models.Proposal.query
                          .order_by(models.Proposal.date.desc())),
    })


@proposals.route('/proposals/<uuid:proposal_id>')
def proposal(proposal_id):
    proposal = (models.Proposal.query
                    .filter_by(id=proposal_id)
                    .first_or_404())
    activity = proposal.activity.order_by(models.ProposalActivityItem.order)
    return flask.render_template('proposals/detail.html', **{
        'proposal': proposal,
        'policy_domain': proposal.policy_domain,
        'sponsorships': [{
                'id': sp.id,
                'mandate': sp.mandate,
                'match_data': flask.json.loads(sp.match.data or '{}'),
            } for sp in proposal.sponsorships],
        'activity': activity.all(),
        'voting_sessions': proposal.voting_sessions.all(),
    })


@proposals.route('/proposals/relevant')
def relevant():
    sponsorships = [s for s in models.Sponsorship.query if s.match.score]
    sponsorships.sort(key=lambda s: s.match.score or 0, reverse=True)
    return flask.render_template('proposals/relevant.html', **{
        'sponsorships': sponsorships,
    })


@job
def ocr_proposal(proposal_id, autoanalyze=False):
    proposal = models.Proposal.query.get(proposal_id)
    pages = ocr_url(proposal.pdf_url)
    proposal.text = '\n\n'.join(pages)
    models.db.session.commit()
    logger.info("done OCR for %s (%d pages)", proposal, len(pages))

    if autoanalyze:
        sponsorships = proposal.sponsorships.all()
        logger.info("scheduling analysis for %d mandates", len(sponsorships))
        for sp in sponsorships:
            mandate = sp.mandate
            if not mandate.minority:
                if (mandate.county is None or
                    mandate.county.geonames_code is None):
                    continue
            analyze_sponsorship.delay(sp.id)


@proposals_manager.command
def ocr_all(number=None, force=False):
    n_jobs = n_skip = n_ok = 0
    for proposal in models.Proposal.query:
        if not proposal.pdf_url:
            n_skip += 1
            continue
        if proposal.text is not None and not force:
            n_ok += 1
            continue

        ocr_proposal.delay(proposal.id)

        n_jobs += 1
        if number and n_jobs >= int(number):
            break

    logger.info("enqueued %d jobs, skipped %d, ok %d", n_jobs, n_skip, n_ok)


@job
@proposals_manager.command
def analyze_sponsorship(sponsorship_id):
    sponsorship = models.Sponsorship.query.get(sponsorship_id)
    proposal = sponsorship.proposal
    text = proposal.title + ' ' + proposal.text
    result = match_text_for_mandate(sponsorship.mandate, text)
    sponsorship.match.data = flask.json.dumps(result)
    if not sponsorship.match.manual:
        sponsorship.match.score = ask.match.get_score_from_data()
    models.db.session.commit()


@proposals_manager.command
def analyze_all(number=None, force=False, minority_only=False):
    n_jobs = n_skip = n_ok = 0
    text_row_ids = models.OcrText.all_ids_for('proposal')
    for sponsorship in models.Sponsorship.query:
        if not force:
            if sponsorship.match.data is not None:
                n_ok += 1
                continue
        if sponsorship.proposal_id not in text_row_ids:
            n_skip += 1
            continue
        if not sponsorship.mandate.minority:
            county = sponsorship.mandate.county
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
