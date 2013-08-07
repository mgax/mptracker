from collections import namedtuple
import re
from jellyfish import jaro_winkler

Token = namedtuple('Token', ['text', 'start', 'end'])
ANY_PUNCTUATION = r'[.,;!?\-()]*'
word_pattern = re.compile(r'\b' + ANY_PUNCTUATION +
                          r'(?P<word>\S+?)' +
                          ANY_PUNCTUATION + r'\b')


def tokenize(text):
    offset = 0
    while True:
        match = word_pattern.search(text, offset)
        if match is None:
            break
        word = match.group('word')
        offset = match.end()
        yield Token(word, match.start('word'), match.end('word'))


def match_names(text, name_list, mp_info={}):
    MP_TITLE_LOOKBEHIND_TOKENS = 7

    matches = []
    tokens = list(tokenize(text))
    for idx, token in enumerate(tokens):
        token_matches = []
        for name in name_list:
            distance = jaro_winkler(name, token.text.lower())
            if distance > .90:
                token_matches.append({
                    'distance': distance,
                    'name': name,
                    'token': token,
                })

        if not token_matches:
            continue

        if mp_info.get('name'):
            mp_name_bits = [t.text.lower() for t in tokenize(mp_info['name'])]
            recent_tokens = tokens[:idx][- MP_TITLE_LOOKBEHIND_TOKENS:]
            recent_text_bits = set(t.text.lower() for t in recent_tokens)
            expected_mp_title_bits = set(mp_name_bits)
            if expected_mp_title_bits.issubset(recent_text_bits):
                continue

        token_matches.sort(key=lambda m: m['distance'])
        matches.append(token_matches[-1])

    return matches
