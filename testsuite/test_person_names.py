def test_match_easy_names():
    from mptracker.scraper.people import match_split_name as m
    assert m('Bar Foo', 'Foo BAR') == ('Foo', 'Bar')
    assert m('Bar Foo Baz', 'Foo Baz BAR') == ('Foo Baz', 'Bar')
    assert m('Baz Bar Foo', 'Foo BAZ BAR') == ('Foo', 'Baz Bar')

    assert m(
        'Băişanu Ştefan-Alexandru',
        'Ştefan-Alexandru BĂIŞANU',
    ) == ('Ştefan-Alexandru', 'Băişanu')
