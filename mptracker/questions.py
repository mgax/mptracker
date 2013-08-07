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
from mptracker.nlp import tokenize


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


name_normalization_map = [
    ('-', ' '),
    ('ș', 's'),
    ('ț', 't'),
    ('ă', 'a'),
    ('â', 'a'),
    ('î', 'i'),
]


def normalize_place_name(name):
    name = name.lower()
    for ch, new_ch in name_normalization_map:
        name = name.replace(ch, new_ch)
    return name


def get_county_names(county_siruta):
    from sirutalib import SirutaDatabase
    siruta = SirutaDatabase()

    def walk_siruta(code):
        name = siruta.get_name(code, prefix=False)
        yield normalize_place_name(name)
        for thing in siruta.get_inf_codes(code):
            yield from walk_siruta(thing)

    names = set(walk_siruta(county_siruta))
    return sorted(names)


def match_and_describe(question):
    from jellyfish import jaro_winkler

    prahova_json_path = (path(flask.current_app.config['DATA_DIR'])
                         / 'prahova-names.json')
    local_names = flask.json.loads(prahova_json_path.text())
    virgil = models.Person.query.filter_by(cdep_id=159).first()
    text_tokens = [token for token in tokenize(question.text)]
    matches = []
    for token in text_tokens:
        for name in local_names:
            distance = jaro_winkler(name, token.text.lower())
            if distance > .90:
                matches.append({
                    'distance': distance,
                    'name': name,
                    'token': token,
                })
    top_matches = sorted(matches,
                         key=lambda m: m['distance'],
                         reverse=True)[:5]

    return {
        'question': question,
        'top_matches': top_matches,
    }


@questions.route('/person/<person_id>/questions')
def person_questions(person_id):
    person = models.Person.query.get_or_404(person_id)
    question_matches = [match_and_describe(q) for q in person.questions]
    return flask.render_template('person_questions.html', **{
        'person': person,
        'question_matches': question_matches,
    })
