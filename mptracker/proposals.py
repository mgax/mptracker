from time import sleep
import logging
import flask
from flask.ext.script import Manager
from mptracker import models
from mptracker.common import ocr_url

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

proposals = flask.Blueprint('proposals', __name__)

proposals_manager = Manager()


@proposals.route('/person/<person_id>/proposals')
def person_proposals(person_id):
    person = models.Person.query.get_or_404(person_id)
    return flask.render_template('person_proposals.html', **{
        'person': person,
        'proposals': list(person.proposals),
    })


@proposals.route('/proposals/<proposal_id>')
def proposal(proposal_id):
    proposal = models.Proposal.query.get_or_404(proposal_id)
    return flask.render_template('proposal.html', **{
        'proposal': proposal,
        'sponsors': list(proposal.sponsors),
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
