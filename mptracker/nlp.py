import re
from collections import namedtuple, defaultdict

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


def prepare_names(name_list):
    out = defaultdict(dict)
    for name in name_list:
        norm_name = normalize(name)
        if norm_name in stop_words:
            continue
        name_words = [t.text for t in tokenize(norm_name)]
        word_count = len(name_words)
        out[word_count][norm_name] = name
    return sorted(out.items())


def match_names(text, name_list, mp_info={}):
    MP_TITLE_LOOKBEHIND_TOKENS = 7

    name_data = prepare_names(name_list)

    matches = []
    tokens = list(tokenize(text))
    for idx in range(len(tokens)):
        token_matches = []
        for word_count, counted_name_list in name_data:
            if idx + word_count > len(tokens):
                continue
            token_window = tokens[idx : idx + word_count]
            token = join_tokens(token_window)

            for stem in [False, True]:
                norm_token = normalize(token.text, stem=stem)
                if norm_token in counted_name_list:
                    distance = 1.0
                    token_matches.append({
                        'distance': distance,
                        'name': counted_name_list[norm_token],
                        'token': token,
                    })

        if not token_matches:
            continue

        token_matches.sort(key=lambda m: len(m['name']))
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
