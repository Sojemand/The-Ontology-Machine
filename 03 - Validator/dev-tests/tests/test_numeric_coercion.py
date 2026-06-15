from __future__ import annotations

from validator_vision.validator.vision import _parse_numeric_token, normalize_text


def test_normalize_text_keeps_zero_false_and_umlauts():
    assert normalize_text(0) == "0"
    assert normalize_text(False) == "false"
    assert normalize_text("Strasse Mueller") == "strasse mueller"


def test_parse_numeric_token_handles_grouped_numbers():
    assert _parse_numeric_token("1.000") == 1000.0
    assert _parse_numeric_token("1,000") == 1000.0
    assert _parse_numeric_token("1.234,56") == 1234.56
    assert _parse_numeric_token("1,234.56") == 1234.56


def test_parse_numeric_token_handles_ocr_group_separators():
    assert _parse_numeric_token("1 234,56") == 1234.56
    assert _parse_numeric_token("1'234.56") == 1234.56
    assert _parse_numeric_token("1\u202f234,56") == 1234.56
    assert _parse_numeric_token("-1 234,56") == -1234.56


def test_parse_numeric_token_rejects_malformed_grouping():
    assert _parse_numeric_token("1,2,3") is None
    assert _parse_numeric_token("1.2.3") is None
    assert _parse_numeric_token("12 34") is None
    assert _parse_numeric_token("12'34") is None
