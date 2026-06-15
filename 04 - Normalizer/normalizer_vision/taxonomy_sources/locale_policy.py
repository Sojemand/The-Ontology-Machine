from __future__ import annotations

import re
from typing import Any, Callable

CONTROL_LOCALE = "en"
_LOCALE_RE = re.compile(r"^[a-z]{2,3}(?:-[a-z0-9]{2,8})*$")


def require_locale(value: Any, *, label: str, require_text: Callable[..., str]) -> str:
    locale = require_text(value, label=label).casefold()
    if not _LOCALE_RE.fullmatch(locale):
        raise ValueError(f"{label} muss ein gueltiger Locale-Code sein.")
    if locale != CONTROL_LOCALE:
        raise ValueError(f"{label} must be {CONTROL_LOCALE!r}; taxonomy/runtime control locales are en-only.")
    return locale


def require_locale_list(value: Any, *, label: str, require_text: Callable[..., str]) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} muss eine Liste von Locale-Codes sein.")
    result: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        locale = require_locale(item, label=f"{label}[{index}]", require_text=require_text)
        if locale in seen:
            raise ValueError(f"{label} enthaelt doppelte Locale: {locale}")
        seen.add(locale)
        result.append(locale)
    return result


def canonical_locale_list(value: Any, *, label: str, require_text: Callable[..., str]) -> list[str]:
    locales = sorted(require_locale_list(value, label=label, require_text=require_text))
    if locales != [CONTROL_LOCALE]:
        raise ValueError(f"{label} must be [{CONTROL_LOCALE!r}]; taxonomy/runtime control locales are en-only.")
    return locales
