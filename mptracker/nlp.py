import sys
import re
import csv
import logging
from collections import namedtuple
from collections import defaultdict
from functools import lru_cache
import flask
from flask.ext.script import Manager
from path import path
from jellyfish import jaro_winkler

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

Token = namedtuple('Token', ['text', 'start', 'end'])
ANY_PUNCTUATION = r'[.,;!?\-()]*'
word_pattern = re.compile(r'\b' + ANY_PUNCTUATION +
                          r'(?P<word>\S+?)' +
                          ANY_PUNCTUATION + r'\b')
name_normalization_map = [
    ('-', ' '),
    ('ș', 's'),
    ('ş', 's'),
    ('ț', 't'),
    ('ţ', 't'),
    ('ă', 'a'),
    ('â', 'a'),
    ('î', 'i'),
]

nlp_manager = Manager()


def normalize(name):
    name = name.lower()
    for ch, new_ch in name_normalization_map:
        name = name.replace(ch, new_ch)
    return name


def tokenize(text):
    offset = 0
    while True:
        match = word_pattern.search(text, offset)
        if match is None:
            break
        word = match.group('word')
        offset = match.end()
        yield Token(word, match.start('word'), match.end('word'))


def join_tokens(tokens):
    text = ' '.join(t.text for t in tokens)
    return Token(text, tokens[0].start, tokens[-1].end)


def match_names(text, name_list, mp_info={}):
    MP_TITLE_LOOKBEHIND_TOKENS = 7
    DISTANCE_THRESHOLD = .97

    matches = []
    tokens = list(tokenize(text))
    for idx in range(len(tokens)):
        token_matches = []
        for name in name_list:
            name_words = name.split()
            if idx + len(name_words) > len(tokens):
                continue
            token_window = tokens[idx : idx + len(name_words)]
            token = join_tokens(token_window)

            distance = jaro_winkler(normalize(name), normalize(token.text))
            if distance >= DISTANCE_THRESHOLD:
                token_matches.append({
                    'distance': distance,
                    'name': name,
                    'token': token,
                })

        if not token_matches:
            continue

        if mp_info.get('name'):
            mp_name_bits = [normalize(t.text)
                            for t in tokenize(mp_info['name'])]
            recent_tokens = tokens[:idx][- MP_TITLE_LOOKBEHIND_TOKENS:]
            recent_text_bits = set(normalize(t.text) for t in recent_tokens)
            expected_mp_title_bits = set(mp_name_bits)
            if len(expected_mp_title_bits & recent_text_bits) >= 2:
                continue

        token_matches.sort(key=lambda m: m['distance'])
        matches.append(token_matches[-1])

    return matches


@nlp_manager.command
def load_placenames():
    columns = ['geonameid', 'name', 'asciiname', 'alternatenames', 'latitude',
               'longitude', 'feature class', 'feature code', 'country code',
               'cc2', 'admin1 code', 'admin2 code', 'admin3 code',
               'admin4 code', 'population', 'elevation', 'dem', 'timezone',
               'modification date']
    reader = csv.DictReader(sys.stdin, delimiter='\t', fieldnames=columns)
    place_names_by_county = defaultdict(set)
    counties = []
    for row in reader:
        adm1_code = row['admin1 code']
        name = row['name']
        county_place_names = place_names_by_county[adm1_code]
        county_place_names.add(name)

        if row['feature code'] == 'ADM1':
            county = {
                'code': adm1_code,
                'name': name,
                'place_names': county_place_names,
            }
            counties.append(county)

    for county in counties:
        county['place_names'] = sorted(county['place_names'])
        out_name = '%s.json' % county['code']
        out_path = path(flask.current_app.root_path) / 'placenames' / out_name
        with out_path.open('w', encoding='utf-8') as f:
            flask.json.dump(county, f, indent=2, sort_keys=True)
            f.write('\n')
        logger.info("Saved county %s (%s) with %d names",
                    county['name'], county['code'], len(county['place_names']))


@lru_cache(100)
def get_placenames(code):
    json_name = '%02d.json' % code
    json_path = path(flask.current_app.root_path) / 'placenames' / json_name
    with json_path.open('r', encoding='utf-8') as f:
        return flask.json.load(f)['place_names']
