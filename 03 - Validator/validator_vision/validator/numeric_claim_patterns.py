from __future__ import annotations

import re

EMBEDDED_DATE_PATTERNS = (
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(r"\b\d{1,2}\.\d{1,2}\.\d{2,4}\b"),
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b"),
    re.compile(r"\b\d{1,2}-\d{1,2}-\d{4}\b"),
)
DIGITISH = "0-9OoIl"
EMBEDDED_NUMERIC_TOKEN_RE = re.compile(
    rf"[-+]?(?=[{DIGITISH}.,'\u00a0\u202f\u2019]*\d)[{DIGITISH}]+(?:[\d., '\u00a0\u202f\u2019]*[{DIGITISH}]+)?"
)
NUMBER_WITH_OPTIONAL_CURRENCY_RE = re.compile(
    rf"^\s*(?:[\u20ac$\u00a3]\s*)?(?P<number>[-+]?(?=[{DIGITISH}.,'\u00a0\u202f\u2019]*\d)[{DIGITISH}]+(?:[\d., '\u00a0\u202f\u2019]*[{DIGITISH}]+)?)(?:\s*(?:\u20ac|eur|usd|chf|gbp|%))?\s*$",
    re.IGNORECASE,
)
CLAIM_TEXT_TRANSLATION = str.maketrans(
    {
        "\u00a0": " ",
        "\u202f": " ",
        "\u2007": " ",
        "\u2019": "'",
        "\u2018": "'",
        "\u201c": '"',
        "\u201d": '"',
    }
)
ZERO_WIDTH_CHARS = {"\u200b", "\u200c", "\u200d", "\ufeff"}
LAYOUT_CONTROL_CHARS = {"\t", "\n", "\r", "\f", "\v"}
OCR_DIGIT_TRANSLATION = str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1"})
CURRENCY_OR_UNIT_RE = re.compile(r"[\u20ac$\u00a3]|\b(?:eur|usd|chf|gbp|netto|brutto|betrag|summe|preis|ust|mwst|%)\b", re.IGNORECASE)
QUANTITY_RE = re.compile(r"\b(?:x|stk|stueck|stÃ¼ck|qty|menge|anzahl|pcs)\b", re.IGNORECASE)
ADDRESS_RE = re.compile(r"\b(?:strasse|straÃŸe|str\.|weg|platz|allee|gasse|ring|ufer|chaussee|plz|postleitzahl)\b", re.IGNORECASE)
IDENTIFIER_RE = re.compile(r"\b(?:iban|bic|hrb|st\.?-?nr|tax|steuer|tel\.?|telefon|fax|auftrag|bestell|kund|rechnung|referenz)\b", re.IGNORECASE)
DECIMAL_RE = re.compile(r"[.,]\d{1,2}$")
POSTAL_CODE_RE = re.compile(r"^\d{5}$")
LABEL_SUFFIX_BEFORE_NUMBER_RE = re.compile(r"(?:^|[^A-Za-z0-9_])[A-Za-z][A-Za-z0-9]{0,15}\.$")
VALUE_UNIT_AFTER_NUMBER_RE = re.compile(r"\s*(?:[\u20ac$\u00a3%]|\b(?:eur|usd|chf|gbp)\b)", re.IGNORECASE)
