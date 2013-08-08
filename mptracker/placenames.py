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


@placenames_manager.command
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
