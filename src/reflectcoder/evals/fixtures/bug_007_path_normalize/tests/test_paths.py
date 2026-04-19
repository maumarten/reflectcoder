from paths import normalize_path


def test_simple_absolute():
    assert normalize_path("/a/b/c") == "/a/b/c"


def test_collapse_multiple_slashes():
    assert normalize_path("/a//b///c") == "/a/b/c"


def test_drops_current_segments():
    assert normalize_path("/a/./b/./c") == "/a/b/c"


def test_resolves_parent_segments():
    assert normalize_path("/a/b/../c") == "/a/c"


def test_parent_at_root_stays_at_root():
    assert normalize_path("/../a") == "/a"


def test_multiple_parents_at_root():
    assert normalize_path("/../../a/b") == "/a/b"


def test_empty_input_returns_dot():
    assert normalize_path("") == "."


def test_dot_input_returns_dot():
    assert normalize_path(".") == "."


def test_dot_slash_returns_dot():
    assert normalize_path("./") == "."


def test_dot_slash_dot_returns_dot():
    assert normalize_path("./.") == "."


def test_root_path_is_preserved():
    assert normalize_path("/") == "/"


def test_trailing_slash_removed_on_non_root():
    assert normalize_path("/a/b/") == "/a/b"


def test_relative_path_preserved():
    assert normalize_path("a/b/c") == "a/b/c"


def test_relative_with_parent():
    assert normalize_path("a/b/../c") == "a/c"


def test_collapse_preserves_absolute_marker():
    assert normalize_path("///a") == "/a"
