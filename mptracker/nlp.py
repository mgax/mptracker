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


def match_names(text, name_list):
    matches = []
    for token in tokenize(text):
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

        token_matches.sort(key=lambda m: m['distance'])
        matches.append(token_matches[-1])

    return matches
