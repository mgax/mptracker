import logging
from collections import defaultdict
import flask
from flask.ext.script import Manager
from flask.ext.rq import job
from mptracker import models
from mptracker.common import ocr_url, csv_lines
from mptracker.nlp import match_text_for_person
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
    n_jobs = n_skip = n_ok = 0
    for question in models.Question.query:
        if not question.pdf_url:
            n_skip += 1
            continue
        if question.text is not None and not force:
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
    result = match_text_for_person(question.person, text)
    question.match.data = flask.json.dumps(result)
    question.match.score = len(result['top_matches'])
    models.db.session.commit()


@questions_manager.command
def analyze_all(number=None, force=False, minority_only=False):
    n_jobs = n_skip = n_ok = 0
    for question in models.Question.query:
        if not force:
            if question.match.data is not None:
                n_ok += 1
                continue
        if question.text is None:
            n_skip += 1
            continue
        if not question.person.minority:
            county = question.person.county
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
def person_index():
    from sqlalchemy import func
    from sqlalchemy.orm import subqueryload
    question_count_for_person = dict(
        models.db.session
            .query(models.Question.person_id,
                   func.count(models.Question.person_id))
            .group_by(models.Question.person_id)
    )
    people_rows = (models.Person.query
                .filter(models.Person.cdep_id != None)
                .options(subqueryload(models.Person.county)))
    people = [{
                'id': p.id,
                'str': str(p),
                'county_name': p.county.name if p.county else '',
                'question_count': question_count_for_person.get(p.id, 0),
            } for p in people_rows]
    people.sort(key=lambda p: p['question_count'], reverse=True)
    return flask.render_template('questions/person_index.html', **{
        'people': people,
    })


@questions.route('/person/<person_id>/questions')
def person_questions(person_id):
    person = models.Person.query.get_or_404(person_id)
    addressee_count = defaultdict(int)
    questions = []
    for q in person.questions:
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
                              mimetype='text/plain')

    addressee_top = sorted(((n, name) for name, n in addressee_count.items()),
                           reverse=True)[:5]

    def sort_key(question):
        if question['is_local_topic_flag']:
            return 11.0
        else:
            return question['score'] or 0
    questions.sort(key=sort_key, reverse=True)
    return flask.render_template('questions/person.html', **{
        'person': person,
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


@questions.route('/questions/<question_id>')
def question_detail(question_id):
    question = models.Question.query.get_or_404(question_id)
    match_result = (flask.json.loads(question.match.data)
                    if question.match.data else None)

    return flask.render_template('questions/detail.html', **{
        'person': question.person,
        'question': question,
        'match_result': match_result,
    })


@questions.route('/questions/<question_id>/save_flags', methods=['POST'])
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
