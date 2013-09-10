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

            yield {
                'name': name,
                'year': year,
                'cdep_number': cdep_number,
                'constituency': int(row['Nr Circumscriptie']),
                'college': int(row['Nr Colegiu']),
                'votes': int(row['Voturi obtinute']),
                'votes_percent': Decimal(row['% Voturi obtinute']),
                'address': txtval(row['Adresa birou parlamentar']),
                'phone': txtval(row['Telefon birou parlamentar']),
            }
