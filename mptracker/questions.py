import logging
from collections import defaultdict
import flask
from flask.ext.script import Manager
from flask.ext.rq import job
from mptracker import models
from mptracker.common import ocr_url, csv_lines
from mptracker.nlp import match_text_for_mandate
from mptracker.auth import require_privilege


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

questions = flask.Blueprint('questions', __name__)

questions_manager = Manager()


@job
def ocr_question(question_id):
    question = models.Question.query.get(question_id)

    pages = ocr_url(question.pdf_url)
    question.text = '\n\n'.join(pages)

    models.db.session.add(question)
    models.db.session.commit()
    logger.info("done OCR for %s (%d pages)", question, len(pages))


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
def analyze_question(question_id):
    question = models.Question.query.get(question_id)
    text = question.title + ' ' + question.text
    result = match_text_for_mandate(question.mandate, text)
    question.match.data = flask.json.dumps(result)
    question.match.score = len(result['top_matches'])
    models.db.session.commit()


@questions_manager.command
def analyze_all(number=None, force=False, minority_only=False):
    text_row_ids = models.OcrText.all_ids_for('question')
    def has_text(question):
        return question.id in text_row_ids

    match_row_ids = models.Match.all_ids_for('question')
    def has_match(question):
        return question.id in match_row_ids

    n_jobs = n_skip = n_ok = 0
    for question in models.Question.query:
        if not force:
            if has_match(question):
                n_ok += 1
                continue
        if not has_text(question):
            n_skip += 1
            continue
        mandate = question.mandate
        if not mandate.minority:
            county = mandate.county
            if (minority_only or
                county is None or
                county.geonames_code is None):
                n_skip += 1
                continue
        analyze_question.delay(question.id)
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
            .query(models.Question.mandate_id,
                   func.count(models.Question.mandate_id))
            .group_by(models.Question.mandate_id)
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
    for q in mandate.questions:
        questions.append({
            'id': q.id,
            'title': q.title,
            'date': q.date,
            'is_local_topic_flag': q.flags.is_local_topic,
            'score': q.match.score or 0,
            'addressee': q.addressee,
        })
        for name in q.addressee.split(';'):
            addressee_count[name.strip()] += 1

    if flask.request.args.get('format') == 'csv':
        cols = ['id', 'title', 'date', 'is_local_topic_flag',
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
def question_bugs():
    Question = models.Question
    questions = (Question.query
                         .join(Question.flags_row)
                            .filter(models.QuestionFlags.is_bug == True)
                         .join(Question.person))
    return flask.render_template('questions/bugs.html', **{
        'questions': questions,
    })


@questions.route('/questions/<uuid:question_id>')
def question_detail(question_id):
    question = models.Question.query.get_or_404(question_id)
    match_result = (flask.json.loads(question.match.data)
                    if question.match.data else None)

    return flask.render_template('questions/detail.html', **{
        'mandate': question.mandate,
        'person': question.mandate.person,
        'question': question,
        'match_result': match_result,
    })


@questions.route('/questions/<uuid:question_id>/save_flags', methods=['POST'])
@require_privilege
def question_save_flags(question_id):
    question = models.Question.query.get_or_404(question_id)
    for name in ['is_local_topic', 'is_bug']:
        if name in flask.request.form:
            value = flask.json.loads(flask.request.form[name])
            setattr(question.flags, name, value)
    models.db.session.commit()
    url = flask.url_for('.question_detail', question_id=question_id)
    return flask.redirect(url)
