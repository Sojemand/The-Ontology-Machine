from __future__ import annotations

import re
from typing import Any

from .governance import EDIT_ENDPOINTS
from .tool_handler_types import ToolFailure

GENERIC_OWNER_EDIT_MODULES = {"orchestrator", "normalizer"}


def _reject_arguments(arguments: dict[str, Any], name: str) -> None:
    if arguments:
        raise ToolFailure(f"{name} akzeptiert keine Argumente.")


def _required_module(arguments: dict[str, Any]) -> str:
    module = _required_text(arguments, "module")
    if module not in EDIT_ENDPOINTS or module not in GENERIC_OWNER_EDIT_MODULES:
        raise ToolFailure(f"Modul hat keine MCP-freigegebene Edit-Surface: {module}")
    return module


def _required_text(arguments: dict[str, Any], key: str) -> str:
    value = _optional_text(arguments, key)
    if not value:
        raise ToolFailure(f"{key} fehlt oder ist ungueltig.")
    return value


def _required_locale_argument(arguments: dict[str, Any], key: str) -> str:
    value = _required_text(arguments, key).replace("_", "-").casefold()
    if not re.fullmatch(r"[a-z]{2}(?:-[a-z0-9]{2,8})*", value):
        raise ToolFailure(f"{key} muss ein gueltiger Locale-Code sein.")
    return value


def _optional_locale_argument(arguments: dict[str, Any], key: str) -> str:
    if key not in arguments or arguments.get(key) in (None, ""):
        return ""
    value = _required_text(arguments, key).replace("_", "-").casefold()
    if not re.fullmatch(r"[a-z]{2}(?:-[a-z0-9]{2,8})*", value):
        raise ToolFailure(f"{key} muss ein gueltiger Locale-Code sein.")
    return value


def _optional_text(arguments: dict[str, Any], key: str) -> str:
    value = arguments.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ToolFailure(f"{key} muss ein String sein.")
    return value.strip()


def _required_mapping(arguments: dict[str, Any], key: str) -> dict[str, Any]:
    value = _optional_mapping(arguments, key)
    if value is None:
        raise ToolFailure(f"{key} fehlt oder ist ungueltig.")
    return value


def _required_list(arguments: dict[str, Any], key: str) -> list[Any]:
    value = arguments.get(key)
    if not isinstance(value, list):
        raise ToolFailure(f"{key} muss eine Liste sein.")
    if not value:
        raise ToolFailure(f"{key} darf nicht leer sein.")
    return list(value)


def _optional_mapping(arguments: dict[str, Any], key: str) -> dict[str, Any] | None:
    value = arguments.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ToolFailure(f"{key} muss ein Objekt sein.")
    return value


def _optional_string_list(arguments: dict[str, Any], key: str) -> list[str]:
    value = arguments.get(key)
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ToolFailure(f"{key} muss eine String-Liste sein.")
    return [item.strip() for item in value if item.strip()]


def _optional_bool(arguments: dict[str, Any], key: str, *, default: bool) -> bool:
    value = arguments.get(key, default)
    if not isinstance(value, bool):
        raise ToolFailure(f"{key} muss ein Bool sein.")
    return value


def _positive_int(value: Any, key: str) -> int:
    if isinstance(value, bool):
        raise ToolFailure(f"{key} muss eine positive Ganzzahl sein.")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ToolFailure(f"{key} muss eine positive Ganzzahl sein.") from None
    if parsed < 1:
        raise ToolFailure(f"{key} muss eine positive Ganzzahl sein.")
    return parsed


def _positive_or_zero_int(value: Any, key: str) -> int:
    if isinstance(value, bool):
        raise ToolFailure(f"{key} muss eine nicht-negative Ganzzahl sein.")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ToolFailure(f"{key} muss eine nicht-negative Ganzzahl sein.") from None
    if parsed < 0:
        raise ToolFailure(f"{key} muss eine nicht-negative Ganzzahl sein.")
    return parsed


def _add_optional(payload: dict[str, Any], arguments: dict[str, Any], key: str) -> None:
    value = _optional_text(arguments, key)
    if value:
        payload[key] = value

__all__ = [name for name in globals() if not name.startswith("__")]
