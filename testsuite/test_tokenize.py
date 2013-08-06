def tokenize(*args, **kwargs):
    from mptracker.nlp import tokenize
    return tokenize(*args, **kwargs)


def test_split_words():
    assert [t.text for t in tokenize("hello there  world")] == \
           ['hello', 'there', 'world']


def test_strip_punctuation():
    assert [t.text for t in tokenize("a, s, d? f!")] == ['a', 's', 'd', 'f']
