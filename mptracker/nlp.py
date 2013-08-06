from collections import namedtuple
import re

Token = namedtuple('Token', ['text'])
word_pattern = re.compile(r'\S+')


def tokenize(text):
    offset = 0
    while True:
        match = word_pattern.search(text, offset)
        if match is None:
            break
        word = match.group()
        offset = match.end()
        word = word.strip(',.;!?-()')
        if word:
            yield Token(word)
