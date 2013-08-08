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
            if name in stop_words:
                continue
            name_words = [t.text for t in tokenize(name)]
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
