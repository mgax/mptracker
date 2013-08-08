from mptracker.nlp import match_names


def test_match_string_in_text():
    text = "hello somethingtheer world"
    match = match_names(text, ['foo', 'somethingthere', 'bar'])
    assert len(match) == 1
    assert 0.98 < match[0]['distance'] < 0.99
    assert match[0]['name'] == 'somethingthere'
    assert match[0]['token'].start == 6
    assert match[0]['token'].end == 20


def test_match_single_name_per_token():
    text = "hello theer world"
    match = match_names(text, ['there', 'theer'])
    assert [m['name'] for m in match] == ['theer']


def test_ignore_mp_constituency():
    text = ("foo bar baz blah blah blah Domnul VIRGIL GURAN, Deputat PNL "
            "Prahova Obiectul întrebării Modificarea Legii Sinaia foo bar")
    match = match_names(text, ['prahova', 'sinaia'],
                        mp_info={'name': "Guran Virgil"})
    assert [m['name'] for m in match] == ['sinaia']


def test_match_regardless_of_diacritics():
    text = "foo bar brașov campina hello world"
    match = match_names(text, ["brasov", "câmpina"])
    assert [m['name'] for m in match] == ['brasov', 'câmpina']


def test_match_multiple_words():
    text = "let's match a complicated bit of text"
    match = match_names(text, ["compicated bit"])
    assert [m['name'] for m in match] == ['compicated bit']
    assert match[0]['name'] == "compicated bit"
    assert match[0]['token'].text == "complicated bit"
    assert match[0]['token'].start == 14
    assert match[0]['token'].end == 29


def test_match_words_with_hyphen():
    text = "something fishy at cluj-napoca today"
    match = match_names(text, ["Cluj-Napoca"])
    assert [m['name'] for m in match] == ["Cluj-Napoca"]
    assert match[0]['token'].text == "cluj napoca"
