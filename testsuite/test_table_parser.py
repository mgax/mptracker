from path import path
import pytest

PAGES_DIR = path(__file__).abspath().parent / 'pages'


def test_row_data():
    from mptracker.scraper.common import TableParser
    table_html = (PAGES_DIR / 'table_ppdd_members.html').text()
    table = TableParser(table_html)
    assert table.headings == ["", "Funcţia", "Nume şi prenume", "Membru din"]

    rows = list(table)
    assert len(rows) == 24
    assert rows[3].td("Funcţia").text() == "Secretari"
    assert rows[3].td("Nume").find('a').attr('href') == \
        '/pls/parlam/structura.mp?idm=221&cam=2&leg=2012'

    assert rows[3].text("Funcţia") == "Secretari"
    assert rows[3].text("Funcţia", inherit=True) == "Secretari"

    assert rows[8].text("Funcţia") == ""
    assert rows[8].text("Funcţia", inherit=True) == "Membri"

    assert rows[3].text("foo bar") == ""
    assert rows[3].text("foo bar", inherit=True) == ""


def test_double_header():
    from mptracker.scraper.common import TableParser
    table_html = (PAGES_DIR / 'table_committee_former_members.html').text()
    table = TableParser(table_html, double_header=True)
    assert table.headings == [
        "", "Deputatul", "Grupul parlamentar",
        "Membru al comisiei | din data", "Membru al comisiei | până în data",
    ]

    rows = list(table)
    assert len(rows) == 3

    assert rows[1].text("Membru al comisiei | până în data") == "08.10.2013"
