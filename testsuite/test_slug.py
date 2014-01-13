import pytest


def test_simple_slug():
    from mptracker.common import generate_slug
    assert generate_slug('foo') == 'foo'
    assert generate_slug('      bar      ') == 'bar'
    assert generate_slug('Foo Bar') == 'foo-bar'
    assert generate_slug('Foo         Bar bAz') == 'foo-bar-baz'
    assert generate_slug('"wtf"') == 'wtf'
    assert generate_slug("___-%") == '-'


def test_sequential():
    from mptracker.common import generate_slug
    values = []
    for c in range(4):
        values.append(generate_slug('foo', lambda v: v not in values))
    assert values == ['foo', 'foo-1', 'foo-2', 'foo-3']


def test_sequential_limit():
    from mptracker.common import generate_slug
    with pytest.raises(RuntimeError):
        generate_slug('foo', lambda v: False)
