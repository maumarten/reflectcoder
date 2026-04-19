from csvp import parse_csv_line


def test_simple_fields():
    assert parse_csv_line("a,b,c") == ["a", "b", "c"]


def test_empty_line_returns_single_empty_field():
    assert parse_csv_line("") == [""]


def test_trailing_comma_produces_trailing_empty_field():
    assert parse_csv_line("a,") == ["a", ""]


def test_leading_comma_produces_leading_empty_field():
    assert parse_csv_line(",a") == ["", "a"]


def test_quoted_field_with_embedded_comma():
    assert parse_csv_line('a,"b,c",d') == ["a", "b,c", "d"]


def test_quoted_field_with_escaped_quote():
    # "hello ""world""" -> hello "world"
    assert parse_csv_line('a,"hello ""world""",b') == ["a", 'hello "world"', "b"]


def test_quoted_empty_field():
    assert parse_csv_line('""') == [""]


def test_quoted_empty_field_between_others():
    assert parse_csv_line('a,"",b') == ["a", "", "b"]


def test_whitespace_preserved():
    assert parse_csv_line("a, b ,c") == ["a", " b ", "c"]


def test_entire_line_quoted():
    assert parse_csv_line('"a,b,c"') == ["a,b,c"]


def test_quote_mid_field_is_literal():
    # Quote not at the start of a field is a literal character.
    assert parse_csv_line('a,b"c,d') == ["a", 'b"c', "d"]


def test_multiple_quoted_fields():
    assert parse_csv_line('"a","b","c"') == ["a", "b", "c"]


def test_quoted_field_with_multiple_embedded_commas():
    assert parse_csv_line('"a,b,c,d"') == ["a,b,c,d"]
