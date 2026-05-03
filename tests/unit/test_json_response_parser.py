from backend.core.ingestion.util.json_response_parser import parse_string_list, parse_object
from backend.core.ingestion.util.template import render_template


def test_parse_string_list_json_array():
    assert parse_string_list('["a", "b", "c"]') == ["a", "b", "c"]


def test_parse_string_list_fallback_lines():
    assert parse_string_list("apple\nbanana\norange") == ["apple", "banana", "orange"]


def test_parse_string_list_empty():
    assert parse_string_list("") == []


def test_parse_string_list_invalid_json():
    assert parse_string_list("{not a list}") == ["{not a list}"]


def test_parse_object_valid():
    assert parse_object('{"key": "value"}') == {"key": "value"}


def test_parse_object_invalid_returns_empty():
    assert parse_object("not json") == {}


def test_parse_object_list_returns_empty():
    assert parse_object('["a", "b"]') == {}


def test_render_template_substitutes_vars():
    assert render_template("Hello {{name}}!", name="World") == "Hello World!"


def test_render_template_none_returns_text():
    assert render_template(None, text="fallback") == "fallback"


def test_render_template_missing_var_left_as_is():
    assert render_template("{{x}} and {{y}}", x="X") == "X and {{y}}"
