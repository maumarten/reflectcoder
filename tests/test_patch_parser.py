"""Unit tests for the defensive patch parser.

These live separate from the LLM-dependent tests so CI can run them without a
Groq key.
"""

from reflectcoder.patch_parser import parse_patch


def test_valid_patch():
    payload = '{"rationale": "fix", "files": {"a.py": "print(1)"}}'
    patch = parse_patch(payload)
    assert patch is not None
    assert patch.files == {"a.py": "print(1)"}
    assert patch.rationale == "fix"


def test_wrapped_in_code_fence():
    payload = '```json\n{"files": {"a.py": "x=1"}}\n```'
    patch = parse_patch(payload)
    assert patch is not None
    assert patch.files == {"a.py": "x=1"}


def test_rejects_path_with_newline():
    payload = '{"files": {"bad\\npath.py": "x=1"}}'
    assert parse_patch(payload) is None


def test_rejects_path_traversal():
    payload = '{"files": {"../etc/passwd": "malicious"}}'
    assert parse_patch(payload) is None


def test_rejects_absolute_posix_path():
    payload = '{"files": {"/etc/hosts": "x"}}'
    assert parse_patch(payload) is None


def test_rejects_absolute_windows_path():
    payload = '{"files": {"C:/Windows/notepad.exe": "x"}}'
    assert parse_patch(payload) is None


def test_rejects_non_string_content():
    payload = '{"files": {"a.py": 42}}'
    assert parse_patch(payload) is None


def test_rejects_string_files_value():
    payload = '{"files": "the whole file content as a string"}'
    assert parse_patch(payload) is None


def test_rejects_empty_files():
    payload = '{"files": {}}'
    assert parse_patch(payload) is None


def test_not_json_returns_none():
    assert parse_patch("this is not json at all") is None


def test_extracts_json_embedded_in_prose():
    payload = 'Here is my patch:\n{"files": {"a.py": "pass"}}\nEnd.'
    patch = parse_patch(payload)
    assert patch is not None
    assert patch.files == {"a.py": "pass"}
