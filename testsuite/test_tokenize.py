def tokenize(*args, **kwargs):
    from mptracker.nlp import tokenize
    return tokenize(*args, **kwargs)


def test_split_words():
    assert [t.text for t in tokenize("hello there  world")] == \
           ['hello', 'there', 'world']


def test_strip_punctuation():
    assert [t.text for t in tokenize("a, s, d? f!")] == ['a', 's', 'd', 'f']


def test_preserve_start_and_end():
    assert [t.start for t in tokenize("a  .sunny,  day!")] == [0, 4, 12]
    assert [t.end for t in tokenize("a  .sunny,  day!")] == [1, 9, 15]
