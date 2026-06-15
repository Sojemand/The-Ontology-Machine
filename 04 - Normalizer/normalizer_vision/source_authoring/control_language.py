from __future__ import annotations

from typing import Any

CONTROL_LOCALE = "en"


def control_locale_or_default(*values: Any, label: str = "runtime_locale") -> str:
    for value in values:
        locale = str(value or "").strip().casefold()
        if not locale:
            continue
        if locale != CONTROL_LOCALE:
            raise ValueError(f"{label} must be {CONTROL_LOCALE!r}; runtime locales are no longer supported.")
    return CONTROL_LOCALE
