from mptracker.nlp import match_names


def test_match_string_in_text():
    text = "hello theer world"
    match = match_names(text, ['foo', 'there', 'bar'])
    assert len(match) == 1
    assert 0.95 < match[0]['distance'] < 0.96
    assert match[0]['name'] == 'there'
    assert match[0]['token'].start == 6
    assert match[0]['token'].end == 11
