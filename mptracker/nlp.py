import re
from collections import namedtuple
from jellyfish import jaro_winkler

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

stop_words = set([
    'romani',
    'valea',
    'langa',
    'lege',
    'legii',
])

signature_stop_words = [
    'circuscripția',
    'uninominal',
    'deputat',
    'deputatul',
    'electorală',
]

stem_suffixes = [
    'ean', # argeșean
    'eana', # argeșeană
    'eni', # argeșeni
    'ene', # argeșene
    'enii', # argeșenii
    'enele', # argeșenele
    'enilor', # argeșenior
    'enelor', # argeșenelor
]


def simple_stem(word):
    for suffix in stem_suffixes:
        if word.endswith(suffix):
            word = word[:-len(suffix)]
            break
    return word


def normalize(name, stem=False):
    name = name.lower()
    for ch, new_ch in name_normalization_map:
        name = name.replace(ch, new_ch)
    if stem:
        name = ' '.join(simple_stem(w) for w in name.split())
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
            if name in stop_words:
                continue
            name_words = [t.text for t in tokenize(name)]
            if idx + len(name_words) > len(tokens):
                continue
            token_window = tokens[idx : idx + len(name_words)]
            token = join_tokens(token_window)

            for stem in [False, True]:
                distance = jaro_winkler(normalize(name),
                                        normalize(token.text, stem=stem))
                if distance >= DISTANCE_THRESHOLD:
                    token_matches.append({
                        'distance': distance,
                        'name': name,
                        'token': token,
                    })

        if not token_matches:
            continue

        token_matches.sort(key=lambda m: m['distance'])
        top_match = token_matches[-1]

        if (normalize(top_match['name']) ==
                normalize(mp_info.get('county_name') or '')):
            mp_name_bits = [t.text for t in tokenize(mp_info.get('name', ''))]
            signature_bits = set(normalize(word) for word in
                                 mp_name_bits + signature_stop_words)

            recent_tokens = tokens[:idx][- MP_TITLE_LOOKBEHIND_TOKENS:]
            recent_text_bits = set(normalize(t.text) for t in recent_tokens)

            if len(signature_bits & recent_text_bits) > 0:
                continue

        matches.append(top_match)

    return matches
