from qs import parse_query_string


def test_simple():
    assert parse_query_string("a=1&b=2") == {"a": "1", "b": "2"}


def test_duplicate_keys_last_wins():
    assert parse_query_string("a=1&a=2") == {"a": "2"}


def test_leading_question_mark_is_stripped():
    assert parse_query_string("?a=1&b=2") == {"a": "1", "b": "2"}


def test_empty_value_is_preserved():
    assert parse_query_string("a=&b=2") == {"a": "", "b": "2"}


def test_value_containing_equals():
    assert parse_query_string("a=1=2") == {"a": "1=2"}


def test_empty_string_returns_empty_dict():
    assert parse_query_string("") == {}
