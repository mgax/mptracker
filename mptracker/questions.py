import csv
import logging
import subprocess
import flask
from flask.ext.script import Manager
from mptracker import models
from mptracker.common import temp_dir
from mptracker.scraper.common import get_cached_session


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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


def ocr_question(url, http_session):
    pages = []
    with temp_dir() as tmp:
        pdf_data = http_session.get(url).content
        pdf_path = tmp / 'document.pdf'
        with pdf_path.open('wb') as f:
            f.write(pdf_data)
        subprocess.check_call(['pdfimages', pdf_path, tmp / 'img'])
        for image_path in tmp.listdir('img-*'):
            subprocess.check_call(['tesseract', image_path, image_path],
                                  stderr=subprocess.DEVNULL)
            text = (image_path + '.txt').text()
            pages.append(text)

    return pages


@questions_manager.command
def ocr_all():
    count = 0
    http_session = get_cached_session('question-pdf')
    for question in models.Question.query:
        url = question.pdf_url
        if not url:
            logger.info("Skipping %s, no URL", question)
            continue
        if question.text:
            logger.info("Skipping %s, already done OCR", question)
            continue
        ocr_pages = ocr_question(url, http_session)
        question.text = '\n\n'.join(ocr_pages)
        models.db.session.add(question)
        models.db.session.commit()
        logger.info("done OCR for %s (%d pages)",
                    question, len(ocr_pages))
        count += 1
    logger.info("Completed OCR for %d questions", count)
