from mptracker.nlp import tokenize, join_tokens


def test_split_words():
    assert [t.text for t in tokenize("hello there  world")] == \
           ['hello', 'there', 'world']


def test_strip_punctuation():
    assert [t.text for t in tokenize("a, s, d? f!")] == ['a', 's', 'd', 'f']


def test_preserve_start_and_end():
    assert [t.start for t in tokenize("a  .sunny,  day!")] == [0, 4, 12]
    assert [t.end for t in tokenize("a  .sunny,  day!")] == [1, 9, 15]


def test_join_tokens():
    tokens = list(tokenize("hello    there  world  is great day"))
    big_token = join_tokens(tokens[1:3])
    assert big_token.text == 'there world'
    assert big_token.start == 9
    assert big_token.end == 21
