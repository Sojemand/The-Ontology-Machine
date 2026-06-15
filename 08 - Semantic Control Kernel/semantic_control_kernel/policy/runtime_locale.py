from __future__ import annotations

DEFAULT_CONTROL_LOCALE = "en"


def control_locale_or_default(*values: object) -> str:
    for value in values:
        locale = str(value or "").strip().casefold()
        if not locale:
            continue
        if locale != DEFAULT_CONTROL_LOCALE:
            raise ValueError(
                f"runtime_locale must be {DEFAULT_CONTROL_LOCALE!r}; runtime locales are no longer supported."
            )
    return DEFAULT_CONTROL_LOCALE
