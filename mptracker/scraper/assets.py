import re
import logging
import xlrd

logger = logging.getLogger(__name__)


def parse_assets(file_path):
    workbook = xlrd.open_workbook(file_path)
    sh = workbook.sheets()[0]
    header = [sh.cell(0, n).value for n in range(sh.ncols)]

    for n in range(1, sh.nrows):
        rv = {
            col['field_name']: convert(col, sh.cell(n, i).value, n)
            for i, col in enumerate(COLUMN_DEFINITIONS)
        }
        for col in COLUMN_DEFINITIONS:
            aggregate_to = col.get('aggregate_to')
            if aggregate_to is not None:
                dest = rv.setdefault(aggregate_to, {})
                to_add = rv.pop(col['field_name'])
                try:
                    aggregate_currencies(dest, to_add)
                except:
                    logger.exception(
                        "Error aggregating %r for row %d: %r <- %r",
                        col['field_name'], n + 1, dest, to_add
                    )
                    return
        for field_name in CURRENCY_FIELDS:
            normalize_currencies(rv[field_name])
        yield rv


def aggregate_currencies(dest, to_add):
    for key in to_add:
        assert key not in dest, "Aggregating duplicate key %r" % key
        dest[key] = to_add[key]


def normalize_currencies(dic):
    dic['TOTAL_EUR'] = int(sum(
        dic[c] * EXCHANGE_RATES_NOV_2013[c]
        for c in dic
    ))


def convert(col, value, n):
    parser = col['parser']
    try:
        return parser(value)
    except (ValueError, AssertionError) as e:
        logger.error(
            "Failed to parse %s at row %d: %r"
            % (col['field_name'], n + 1, value)
        )
        return col['fallback']


def land_area(value):
    if isinstance(value, str):
        if '+' in value:
            return sum(land_area(v) for v in value.split('+'))
        if 'ha' in value:
            return number(value.replace('ha', '')) * 10000
        if '/' in value:
            a, b = value.split('/')
            return number(a) / number(b)
    return number(value)


def integer(value):
    return int(value or 0)


def house_count(value):
    if isinstance(value, str):
        value = re.sub(r'garaj[e]?', value, '').split('+')[0]
    return integer(value)


def number(value):
    if isinstance(value, float):
        return value
    return float(value.replace(',', '.') or 0)


def create_currency_parser(default_currency='RON'):
    def parse(value):
        if not value:
            return {}

        out = {}
        for part in str(value).split("+"):
            bits = part.strip().replace('(', '').replace(')', '').split()
            if len(bits) == 1:
                assert default_currency is not None, \
                    "Expected currency and no default currency is set"
                currency = default_currency
                [amount] = bits
            elif len(bits) == 2:
                [amount, currency] = bits
            else:
                assert False, "Unexpected: %r (original value: %r)" \
                    % (bits, value)

            currency = currency.upper()
            if currency in CURRENCY_RENAME:
                currency = CURRENCY_RENAME[currency]
            assert currency in EXCHANGE_RATES_NOV_2013, \
                "Unknown currency %r" % currency
            assert currency not in out, "Duplicate currency %r" % currency
            out[currency] = number(amount)

        return out

    return parse


# source: http://www.ecb.europa.eu/stats/exchange/eurofxref/html/index.en.html
EXCHANGE_RATES_NOV_2013 = {
    'RON': 1 / 4.44,
    'EUR': 1,
    'USD': 1 / 1.35,
    'CHF': 1 / 1.23,
    'GBP': 1 / 0.846,
    'HUF': 1 / 296.5,
}

CURRENCY_RENAME = {
    'E': 'EUR',
}


COLUMN_DEFINITIONS = [
    {
        'heading': 'Nume',
        'field_name': 'person_name',
        'parser': str,
    },
    {
        'heading': 'Judet',
        'field_name': 'county',
        'parser': str,
    },
    {
        'heading': 'Nr Circumscriptie',
        'field_name': 'constituency',
        'parser': integer,
    },
    {
        'heading': 'Nr Terenuri agricole',
        'field_name': 'land_agri_count',
        'parser': integer,
    },
    {
        'heading': 'Suprafata totala terenuri agricole',
        'field_name': 'land_agri_area',
        'parser': land_area,
    },
    {
        'heading': 'Nr Terenuri intravilan',
        'field_name': 'land_city_count',
        'parser': integer,
    },
    {
        'heading': 'Suprafata totala terenuri intravilan',
        'field_name': 'land_city_area',
        'parser': land_area,
    },
    {
        'heading': 'Nr Apartamente',
        'field_name': 'realty_apartment_count',
        'parser': house_count,
    },
    {
        'heading': 'Nr Case',
        'field_name': 'realty_house_count',
        'parser': house_count,
    },
    {
        'heading': 'Nr spatii comericale/ productie',
        'field_name': 'realty_business_count',
        'parser': house_count,
    },
    {
        'heading': 'Nr mijloace transport',
        'field_name': 'vehicle_count',
        'parser': integer,
    },
    {
        'heading': 'Valoare totala bijuterii, arta',
        'field_name': 'valuables_value',
        'parser': create_currency_parser(default_currency='RON'),
    },
    {
        'heading': 'Valoare totala bunuri instrainate in ultimele 12 luni',
        'field_name': 'sales_value',
        'parser': create_currency_parser(default_currency='RON'),
    },
    {
        'heading': 'Valoare Totala Conturi Euro',
        'field_name': 'acct_eur_value',
        'parser': create_currency_parser(default_currency='EUR'),
        'aggregate_to': 'acct_value',
    },
    {
        'heading': 'Valoare Totala Conturi USD',
        'field_name': 'acct_usd_value',
        'parser': create_currency_parser(default_currency='USD'),
        'aggregate_to': 'acct_value',
    },
    {
        'heading': 'Valoare Totala Conturi Lei',
        'field_name': 'acct_ron_value',
        'parser': create_currency_parser(default_currency='RON'),
        'aggregate_to': 'acct_value',
    },
    {
        'heading': 'Valoare Totala Imprumuturi, Plasamente Euro',
        'field_name': 'invest_eur_value',
        'parser': create_currency_parser(default_currency='EUR'),
        'aggregate_to': 'invest_value',
    },
    {
        'heading': 'Valoare Totala Imprumuturi, Plasamente Lei',
        'field_name': 'invest_ron_value',
        'parser': create_currency_parser(default_currency='RON'),
        'aggregate_to': 'invest_value',
    },
    {
        'heading': 'Valoare Totala Datorii Euro',
        'field_name': 'debt_eur_value',
        'parser': create_currency_parser(default_currency='EUR'),
        'aggregate_to': 'debt_value',
    },
    {
        'heading': 'Valoare Totala Datorii Lei',
        'field_name': 'debt_ron_value',
        'parser': create_currency_parser(default_currency='RON'),
        'aggregate_to': 'debt_value',
    },
    {
        'heading': 'Valoare Totala Datorii alta valuta',
        'field_name': 'debt_etc_value',
        'parser': create_currency_parser(default_currency=None),
        'aggregate_to': 'debt_value',
        'fallback': {},
    },
    {
        'heading': 'Valoare Totala cadouri, servicii Euro',
        'field_name': 'gift_eur_value',
        'parser': create_currency_parser(default_currency='EUR'),
        'aggregate_to': 'gift_value',
    },
    {
        'heading': 'Valoare Totala cadouri, servicii Lei',
        'field_name': 'gift_ron_value',
        'parser': create_currency_parser(default_currency='RON'),
        'aggregate_to': 'gift_value',
    },
    {
        'heading': 'Venituri totale ultimul an (inclusiv sot/ sotie/ copii)',
        'field_name': 'family_income_value',
        'parser': create_currency_parser(default_currency='RON'),
    },
]


CURRENCY_FIELDS = ['acct_value', 'debt_value', 'family_income_value',
    'gift_value', 'invest_value', 'sales_value', 'valuables_value']
