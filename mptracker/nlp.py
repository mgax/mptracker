from collections import namedtuple

Token = namedtuple('Token', ['text'])


def tokenize(text):
    for word in text.split():
        word = word.strip(',.;!?-()')
        if word:
            yield Token(word)
