import csv
import re
from decimal import Decimal


def txtval(val):
    val = val.strip()
    if val == '0':
        return None
    elif not val:
        return None
    else:
        return val


def emailval(val):
    val = txtval(val)
    if not val:
        return None
    else:
        return ' '.join([v.strip(',;') for v in val.split()])


def read_person_xls(xls_path):
    with open(xls_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for n, row in enumerate(reader, 1):
            name = row['Nume']
            cdep_url = row['Link pagina pers cdep.ro']
            url_match = re.match(r'http://www.cdep.ro/pls/parlam/structura.mp'
                                 r'\?idm=(?P<cdep_number>\d+)&cam=2'
                                 r'&leg=(?P<year>\d{4})',
                                 cdep_url)
            if url_match is None:
                print("Skipping record", n, "name:", name)
                continue
            year = int(url_match.group('year'))
            cdep_number = int(url_match.group('cdep_number'))
            if (year, cdep_number) == (2008, 251):
                (year, cdep_number) = (2012, 302)
                name = "Potor Călin"
            assert year == 2012
            if cdep_number == 410:
                name += ' Ștefan'
            if cdep_number == 102:
                name = 'Dîrzu Ioan'

            if (year, cdep_number) == (2012, 410):
                assert 'Zgonea' in name
                if row['Telefon birou parlamentar'] == '0':
                    continue

            committees = []
            for k in ['Comisia Permanenta 1', 'Comisia Permanenta 2']:
                committee_name = txtval(row[k])
                if committee_name:
                    committees.append({'name': committee_name,
                                       'role': txtval(row['Functie in ' + k])})

            yield {
                'name': name,
                'year': year,
                'cdep_number': cdep_number,
                'constituency': int(row['Nr Circumscriptie']),
                'college': int(row['Nr Colegiu']),
                'election_votes': int(row['Voturi obtinute']),
                'election_votes_percent': Decimal(row['% Voturi obtinute']),
                'address': txtval(row['Adresa birou parlamentar']),
                'phone': txtval(row['Telefon birou parlamentar']),
                'candidate_party': txtval(
                    row['Partid pentru care a candidat 2012']),
                'person_data': {
                    'year_born': int(row['Anul nasterii']),
                    'education': txtval(row['Educatie']),
                    'website_url': txtval(row['Website ']),
                    'blog_url': txtval(row['Blog']),
                    'email_value': emailval(row['Email']),
                    'facebook_url': txtval(row['Facebook']),
                    'twitter_url': txtval(row['Twitter']),
                },
                'committees': committees,
                'mp_group': {
                    'short_name': txtval(row['Grup parlamentar']),
                    'role': txtval(row['Functie in grupul parlamentar']),
                },
            }


def read_person_contact(csv_path):
    header = ['Nume', 'Link pagina pers cdep.ro', 'Adresa birou parlamentar',
              'Telefon birou parlamentar', 'Anul nasterii', 'Educatie',
              'Website ', 'Blog', 'Email', 'Facebook', 'Twitter']
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for field in header:
            if field not in reader.fieldnames:
                raise ValueError(
                    'Invalid file, field {0} missing from header'.format(field)
                )
        for n, row in enumerate(reader, 1):
            name = row['Nume']
            cdep_url = row['Link pagina pers cdep.ro']
            url_match = re.match(r'http://www.cdep.ro/pls/parlam/structura.mp'
                                 r'\?idm=(?P<cdep_number>\d+)&cam=2'
                                 r'&leg=(?P<year>\d{4})',
                                 cdep_url)
            if url_match is None:
                print("Skipping record", n, "name:", name)
                continue
            year = int(url_match.group('year'))
            cdep_number = int(url_match.group('cdep_number'))
            if year != 2012:
                print("Ignoring year", year, "name:", name)
                continue

            if name == 'Varol AMET':
                name = 'Amet Varol'

            yield {
                'name': name,
                'year': year,
                'cdep_number': cdep_number,
                'address': txtval(row['Adresa birou parlamentar']),
                'phone': txtval(row['Telefon birou parlamentar']),
                'person_data': {
                    'year_born': int(row['Anul nasterii']),
                    'education': txtval(row['Educatie']),
                    'website_url': txtval(row['Website ']),
                    'blog_url': txtval(row['Blog']),
                    'email_value': emailval(row['Email']),
                    'facebook_url': txtval(row['Facebook']),
                    'twitter_url': txtval(row['Twitter']),
                },
            }
