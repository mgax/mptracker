import csv
import logging
import subprocess
import flask
from flask.ext.script import Manager
from flask.ext.rq import job
from path import path
from mptracker import models
from mptracker.common import temp_dir
from mptracker.scraper.common import get_cached_session
from mptracker.nlp import match_names, get_placenames


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

questions = flask.Blueprint('questions', __name__)

questions_manager = Manager()

@questions_manager.command
def load(csv_path):
    person_matcher = models.PersonMatcher()

    existing = {(q.number, q.date): q for q in models.Question.query}

    n_add = n_update = n_ok = 0
    with open(csv_path, 'r') as csv_file:
        csv_doc = csv.DictReader(csv_file)
        for row in csv_doc:
            row['date'] = models.parse_date(row.pop('date'))
            person = person_matcher.get_person(row.pop('person_name'),
                                               int(row.pop('person_cdep_id')),
                                               strict=True)
            row['person'] = person

            if (row['number'], row['date']) in existing:
                question = existing[row['number'], row['date']]
                changed = False
                for k in row:
                    if getattr(question, k) != row[k]:
                        setattr(question, k, row[k])
                        changed = True

                if not changed:
                    n_ok += 1
                    continue

                n_update += 1
                logger.info("Updating question %s/%s",
                            row['number'], row['date'])

            else:
                question = models.Question(**row)
                n_add += 1
                logger.info("Adding question %s/%s",
                            row['number'], row['date'])

            models.db.session.add(question)

    models.db.session.commit()
    logger.info("Created %d, updated %d, found ok %d.", n_add, n_update, n_ok)


@job
def ocr_question(question_id):
    question = models.Question.query.get(question_id)
    http_session = get_cached_session('question-pdf')

    pages = []
    with temp_dir() as tmp:
        pdf_data = http_session.get(question.pdf_url).content
        pdf_path = tmp / 'document.pdf'
        with pdf_path.open('wb') as f:
            f.write(pdf_data)
        subprocess.check_call(['pdfimages', pdf_path, tmp / 'img'])
        for image_path in sorted(tmp.listdir('img-*'))[:10]:
            subprocess.check_call(['tesseract',
                                   image_path, image_path,
                                   '-l', 'ron'],
                                  stderr=subprocess.DEVNULL)
            text = (image_path + '.txt').text()
            pages.append(text)

    question.text = '\n\n'.join(pages)

    models.db.session.add(question)
    models.db.session.commit()
    logger.info("done OCR for %s (%d pages)", question, len(pages))


@questions_manager.command
def ocr_all(number=None):
    count = 0
    for question in models.Question.query:
        if not question.pdf_url:
            logger.info("Skipping %s, no URL", question)
            continue
        if question.text:
            logger.info("Skipping %s, already done OCR", question)
            continue
        ocr_question.delay(question.id)
        count += 1
        if number and count >= int(number):
            break
    logger.info("enqueued %d jobs", count)


def match_question(question):
    local_names = get_placenames(question.person.county.geonames_code)

    mp_info = {'name': question.person.name}
    matches = match_names(question.text, local_names, mp_info=mp_info)
    top_matches = sorted(matches,
                         key=lambda m: m['distance'],
                         reverse=True)[:10]
    return {'top_matches': top_matches}


@job
@questions_manager.command
def analyze_question(question_id):
    question = models.Question.query.get(question_id)
    result = match_question(question)
    question.match_data = flask.json.dumps(result)
    question.match_score = len(result['top_matches'])
    models.db.session.commit()


@questions_manager.command
def analyze_all(number=None, force=False):
    n_jobs = n_skip = n_ok = 0
    for question in models.Question.query:
        if not force:
            if question.match_data is not None:
                n_ok += 1
                continue
        county = question.person.county
        if (question.text is None or
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
                .filter(models.Person.cdep_id)
                .options(subqueryload(models.Person.county)))
    people = [{
                'id': p.id,
                'name': p.name,
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
    questions = list(person.questions)
    questions = [{
            'id': q.id,
            'title': q.title,
            'date': q.date,
            'score': q.match_score,
        } for q in person.questions]
    questions.sort(key=lambda q: q['score'], reverse=True)
    return flask.render_template('questions/person.html', **{
        'person': person,
        'questions': questions,
    })


@questions.route('/questions/<question_id>')
def question_detail(question_id):
    question = models.Question.query.get_or_404(question_id)
    match_result = (flask.json.loads(question.match_data)
                    if question.match_data else None)

    return flask.render_template('questions/detail.html', **{
        'person': question.person,
        'question': question,
        'match_result': match_result,
    })
