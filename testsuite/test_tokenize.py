def tokenize(*args, **kwargs):
    from mptracker.questions import tokenize
    return tokenize(*args, **kwargs)


def test_split_words():
    assert [t for t in tokenize("hello there  world")] \
        == ['hello', 'there', 'world']


def test_strip_punctuation():
    assert [t for t in tokenize("a, s, d? f!")] == ['a', 's', 'd', 'f']
