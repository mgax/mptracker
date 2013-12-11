import logging
from collections import defaultdict
from sqlalchemy import func
from sqlalchemy.orm import joinedload
import flask
from flask.ext.script import Manager
from flask.ext.rq import job
from mptracker import models
from mptracker.common import ocr_url, csv_lines, buffer_on_disk
from mptracker.nlp import match_text_for_mandate
from mptracker.auth import require_privilege


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

questions = flask.Blueprint('questions', __name__)

questions_manager = Manager()


@job
def ocr_question(question_id, autoanalyze=False):
    question = models.Question.query.get(question_id)

    pages = ocr_url(question.pdf_url)
    question.text = '\n\n'.join(pages)

    models.db.session.add(question)
    models.db.session.commit()
    logger.info("done OCR for %s (%d pages)", question, len(pages))

    if autoanalyze:
        asked = question.asked.all()
        logger.info("scheduling analysis for %d mandates", len(asked))
        for ask in asked:
            mandate = ask.mandate
            if not mandate.minority:
                if (mandate.county is None or
                    mandate.county.geonames_code is None):
                    continue
            analyze.delay(ask.id)


@questions_manager.command
def ocr_all(number=None, force=False):
    text_row_ids = models.OcrText.all_ids_for('question')
    def has_text(question):
        return question.id in text_row_ids

    n_jobs = n_skip = n_ok = 0

    for question in models.Question.query:
        if not question.pdf_url:
            n_skip += 1
            continue
        if has_text(question) and not force:
            n_ok += 1
            continue
        ocr_question.delay(question.id)
        n_jobs += 1
        if number and n_jobs >= int(number):
            break
    logger.info("enqueued %d jobs, skipped %d, ok %d", n_jobs, n_skip, n_ok)


@job
@questions_manager.command
def analyze(ask_id):
    ask = models.Ask.query.get(ask_id)
    text = ask.question.title + ' ' + ask.question.text
    result = match_text_for_mandate(ask.mandate, text)
    ask.match.data = flask.json.dumps(result)
    ask.match.score = len(result['top_matches'])
    models.db.session.commit()


@questions_manager.command
def analyze_all(number=None, force=False, minority_only=False):
    text_row_ids = models.OcrText.all_ids_for('question')
    def has_text(question):
        return question.id in text_row_ids

    match_row_ids = models.Match.all_ids_for('ask')
    def has_match(ask):
        return ask.id in match_row_ids

    n_jobs = n_skip = n_ok = 0
    for ask in models.Ask.query.join(models.Ask.question):
        if not force:
            if has_match(ask):
                n_ok += 1
                continue
        if not has_text(ask.question):
            n_skip += 1
            continue
        mandate = ask.mandate
        if not mandate.minority:
            county = mandate.county
            if (minority_only or
                county is None or
                county.geonames_code is None):
                n_skip += 1
                continue
        analyze.delay(ask.id)
        n_jobs += 1
        if number and n_jobs >= int(number):
            break
    logger.info("enqueued %d jobs, skipped %d, ok %d", n_jobs, n_skip, n_ok)


@questions.route('/questions/')
def mandate_index():
    from sqlalchemy import func
    from sqlalchemy.orm import subqueryload
    question_count_for_mandate = dict(
        models.db.session
            .query(models.Ask.mandate_id,
                   func.count(models.Ask.mandate_id))
            .group_by(models.Ask.mandate_id)
    )
    mandate_rows = (models.Mandate.query
                        .options(subqueryload(models.Mandate.county))
                        .options(subqueryload(models.Mandate.person)))
    mandates = [{
            'id': m.id,
            'person_id': m.person.id,
            'person': str(m.person),
            'county_name': m.county.name if m.county else '',
            'question_count': question_count_for_mandate.get(m.id, 0),
        } for m in mandate_rows]
    mandates.sort(key=lambda m: m['question_count'], reverse=True)
    return flask.render_template('questions/mandate_index.html', **{
        'mandates': mandates,
    })


@questions.route('/mandate/<uuid:mandate_id>/questions')
def mandate_questions(mandate_id):
    mandate = (models.Mandate.query
                     .filter_by(id=mandate_id)
                     .join(models.Mandate.person)
                     .first_or_404())
    addressee_count = defaultdict(int)
    questions = []
    for ask in mandate.asked.join(models.Question):
        q = ask.question
        questions.append({
            'id': q.id,
            'title': q.title,
            'date': q.date,
            'question_type': q.type,
            'addressee': q.addressee,
            'is_local_topic_flag': ask.get_meta('is_local_topic'),
            'score': ask.match.score or 0,
        })
        for name in q.addressee.split(';'):
            addressee_count[name.strip()] += 1

    if flask.request.args.get('format') == 'csv':
        cols = ['id', 'title', 'date', 'question_type', 'is_local_topic_flag',
                'score', 'addressee']
        return flask.Response(csv_lines(cols, questions),
                              mimetype='text/csv')

    addressee_top = sorted(((n, name) for name, n in addressee_count.items()),
                           reverse=True)[:5]

    def sort_key(question):
        if question['is_local_topic_flag']:
            return 11.0
        else:
            return question['score'] or 0
    questions.sort(key=sort_key, reverse=True)
    return flask.render_template('questions/mandate.html', **{
        'mandate': mandate,
        'questions': questions,
        'addressee_top': addressee_top,
    })


@questions.route('/questions/bugs')
def bugs():
    return flask.render_template('questions/bugs.html', **{
        'questions': iter(models.Question.query_by_key('is_bug')),
    })


@questions.route('/questions/new')
def new():
    return flask.render_template('questions/new.html', **{
        'questions': iter(models.Question.query_by_key('new')),
    })


@questions.route('/questions/<uuid:question_id>')
def question_detail(question_id):
    question = models.Question.query.get_or_404(question_id)
    return flask.render_template('questions/detail.html', **{
        'question': question,
        'policy_domain': question.policy_domain,
        'asked': [{
                'id': ask.id,
                'mandate': ask.mandate,
                'match_data': flask.json.loads(ask.match.data or '{}'),
                'flags': ask.get_meta_dict(),
            } for ask in question.asked],
    })


@questions.route('/questions/ask_flags/<uuid:ask_id>', methods=['POST'])
@require_privilege
def ask_save_flags(ask_id):
    ask = models.Ask.query.get_or_404(ask_id)
    for name in ['is_local_topic', 'is_bug', 'new']:
        if name in flask.request.form:
            value = flask.json.loads(flask.request.form[name])
            ask.set_meta(name, value)
    models.db.session.commit()
    url = flask.url_for('.question_detail', question_id=ask.question_id)
    return flask.redirect(url)


@questions.route('/questions/_dump/questions.csv')
def question_dump():
    cols = ['name', 'legislature', 'date', 'title', 'score']
    ask_query = (
        models.Ask.query
        .options(
            joinedload('question'),
            joinedload('mandate'),
            joinedload('mandate.person'),
            joinedload('match_row'),
        )
    )
    def make_row(ask):
        score = ask.match.score
        return {
            'name': ask.mandate.person.name,
            'legislature': str(ask.mandate.year),
            'date': str(ask.question.date),
            'title': str(ask.question.title),
            'score': '' if score is None else str(score),
        }
    rows = (make_row(ask) for ask in ask_query.yield_per(10))
    data = buffer_on_disk(csv_lines(cols, rows))
    return flask.Response(data, mimetype='text/csv')
