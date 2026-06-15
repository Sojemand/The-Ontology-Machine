"""Validation stage for readonly SQL and search filter boundaries."""

from __future__ import annotations

import logging
import re

from .types import PreparedSqlStatement, SearchFilter

logger = logging.getLogger(__name__)

_FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|DETACH|REINDEX|VACUUM|PRAGMA)\b",
    re.IGNORECASE,
)
_SELECT_OR_WITH = re.compile(r"^(SELECT|WITH)\b", re.IGNORECASE)
_ALLOWED_FILTERS = frozenset(
    {
        "document_type",
        "category",
        "subcategory",
        "language",
        "validator_status",
        "is_scan",
        "projection_id",
        "materialization_state",
        "entity_type",
        "role_type",
        "promotion_slot",
        "promotion_value",
    }
)
_PROMOTION_FILTER_PREFIXES = ("promotion:", "slot:")


def _scan_sql(sql: str) -> tuple[str, list[int], int | None]:
    result: list[str] = []
    semicolons: list[int] = []
    last_significant_index: int | None = None
    state = "normal"
    index = 0

    while index < len(sql):
        char = sql[index]
        nxt = sql[index + 1] if index + 1 < len(sql) else ""

        if state == "normal":
            if char == "'":
                state = "single_quote"
                result.append(" ")
            elif char == '"':
                state = "double_quote"
                result.append(" ")
            elif char == "[":
                state = "bracket"
                result.append(" ")
            elif char == "`":
                state = "backtick"
                result.append(" ")
            elif char == "-" and nxt == "-":
                state = "line_comment"
                result.extend((" ", " "))
                index += 1
            elif char == "/" and nxt == "*":
                state = "block_comment"
                result.extend((" ", " "))
                index += 1
            else:
                result.append(char)
                if char == ";":
                    semicolons.append(len(result) - 1)
            if not char.isspace() and state not in {"line_comment", "block_comment"}:
                last_significant_index = index
        elif state == "single_quote":
            result.append("\n" if char == "\n" else " ")
            if char == "'" and nxt == "'":
                result.append(" ")
                index += 1
            elif char == "'":
                state = "normal"
            if not char.isspace():
                last_significant_index = index
        elif state == "double_quote":
            result.append("\n" if char == "\n" else " ")
            if char == '"':
                state = "normal"
            if not char.isspace():
                last_significant_index = index
        elif state == "bracket":
            result.append("\n" if char == "\n" else " ")
            if char == "]":
                state = "normal"
            if not char.isspace():
                last_significant_index = index
        elif state == "backtick":
            result.append("\n" if char == "\n" else " ")
            if char == "`":
                state = "normal"
            if not char.isspace():
                last_significant_index = index
        elif state == "line_comment":
            if char == "\n":
                result.append("\n")
                state = "normal"
            else:
                result.append(" ")
        else:
            if char == "*" and nxt == "/":
                result.extend((" ", " "))
                state = "normal"
                index += 1
            else:
                result.append("\n" if char == "\n" else " ")

        index += 1

    return "".join(result), semicolons, last_significant_index


def prepare_sql_statement(sql: str) -> PreparedSqlStatement:
    masked_sql, _ignored_semicolons, last_significant_index = _scan_sql(sql)
    if last_significant_index is None:
        return PreparedSqlStatement("", "", False)

    statement = sql[: last_significant_index + 1].strip()
    masked_statement, semicolons, _ = _scan_sql(statement)
    has_trailing_semicolon = bool(semicolons) and semicolons[-1] == len(masked_statement) - 1
    if semicolons[:-1] or (semicolons and not has_trailing_semicolon):
        raise ValueError("Nur genau ein SQL-Statement erlaubt")
    return PreparedSqlStatement(statement, masked_statement, has_trailing_semicolon)


def validate_readonly_query(sql: str) -> PreparedSqlStatement:
    prepared = prepare_sql_statement(sql)
    masked_leading = prepared.masked_statement.lstrip()
    if not _SELECT_OR_WITH.match(masked_leading):
        raise ValueError(f"Nur SELECT-Statements erlaubt, erhalten: {prepared.statement[:50]}...")
    match = _FORBIDDEN_SQL.search(prepared.masked_statement)
    if match:
        raise ValueError(f"Verbotene SQL-Operation: {match.group(0)}")
    return prepared


def validate_filters(filters: dict[str, object] | None) -> list[SearchFilter]:
    validated: list[SearchFilter] = []
    if not filters:
        return validated

    for key, value in filters.items():
        if key not in _ALLOWED_FILTERS and not key.startswith(_PROMOTION_FILTER_PREFIXES):
            logger.warning("Unerlaubter Filter ignoriert: %s", key)
            continue
        validated.append(SearchFilter(key=key, value=value))
    return validated
