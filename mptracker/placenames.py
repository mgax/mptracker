import sys
import csv
import logging
from collections import defaultdict
from functools import lru_cache
from path import path
import flask
from flask.ext.script import Manager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

placenames_manager = Manager()


def fix_comma_below(text):
    return (text.replace('ş', 'ș')
                .replace('Ş', 'Ș')
                .replace('ţ', 'ț')
                .replace('Ţ', 'Ț'))


def strip_prefix(name):
    for prefix in ['Județul ', 'Municipiul ', 'Oraș ', 'Comuna ']:
        if name.startswith(prefix):
            return name[len(prefix):]
    else:
        return name


stop_words = [
    "agenția",
    "ministerul",
]


class SirutaLoader:

    def __init__(self):
        from sirutalib import SirutaDatabase
        self.siruta = SirutaDatabase()
        self.county_code = {}
        for entry in self.siruta._data.values():
            if entry['type'] == 40:
                name = strip_prefix(entry['name'].title())
                self.county_code[name] = entry['siruta']

    def walk_siruta(self, code):
        name = self.siruta.get_name(code, prefix=False)
        yield name.title()
        for thing in self.siruta.get_inf_codes(code):
            yield from self.walk_siruta(thing)

    def get_siruta_names(self, county_name):
        code = self.county_code[county_name]
        names = set(self.walk_siruta(code))
        return sorted(names)


@placenames_manager.command
def load_placenames():
    columns = ['geonameid', 'name', 'asciiname', 'alternatenames', 'latitude',
               'longitude', 'feature class', 'feature code', 'country code',
               'cc2', 'admin1 code', 'admin2 code', 'admin3 code',
               'admin4 code', 'population', 'elevation', 'dem', 'timezone',
               'modification date']
    siruta_loader = SirutaLoader()
    reader = csv.DictReader(sys.stdin, delimiter='\t', fieldnames=columns)
    place_names_by_county = defaultdict(set)
    counties = []
    for row in reader:
        adm1_code = int(row['admin1 code']) if row['admin1 code'] else None
        name = strip_prefix(fix_comma_below(row['name']))
        if any(w in name.lower() for w in stop_words):
            continue
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
        county['place_names'].update(
            siruta_loader.get_siruta_names(county['name']))
        county['place_names'] = sorted(county['place_names'])
        out_name = '%02d.json' % county['code']
        out_path = (path(flask.current_app.root_path) /
                    'placename_data' / out_name)
        with out_path.open('w', encoding='utf-8') as f:
            flask.json.dump(county, f, indent=2, sort_keys=True)
            f.write('\n')
        logger.info("Saved county %s (%s) with %d names",
                    county['name'], county['code'], len(county['place_names']))


@lru_cache(100)
def get_county_data(code):
    json_name = '%02d.json' % code
    json_path = (path(flask.current_app.root_path) /
                 'placename_data' / json_name)
    with json_path.open('r', encoding='utf-8') as f:
        return flask.json.load(f)


@placenames_manager.command
def expand_minority_names():
    from mptracker.scraper.common import Scraper, get_cached_session, pqitems
    scraper = Scraper(get_cached_session(), use_cdep_opener=False)
    doc = get_minority_names()
    roots = doc['root_names']
    names = set()
    for root in roots:
        url = ('http://dexonline.ro/definitie'
               '/{root}/paradigma'.format(root=root))
        page = scraper.fetch_url(url)
        for td in pqitems(page, 'table.lexem td.form'):
            names.add(td.text().replace(' ', ''))
    if '—' in names:
        names.remove('—')
    doc['search_names'] = sorted(names)
    print(flask.json.dumps(doc, indent=2, sort_keys=True))


@lru_cache()
def get_minority_names():
    json_path = (path(flask.current_app.root_path) /
                 'placename_data' / 'minority.json')
    with json_path.open('r', encoding='utf-8') as f:
        return flask.json.load(f)
