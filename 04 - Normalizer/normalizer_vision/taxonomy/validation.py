"""Hard validation boundaries for taxonomy inputs and lookups."""
from __future__ import annotations

from .types import JsonDict, MASTER_REQUIRED_KEYS, PROJECTION_REQUIRED_KEYS, PROJECTION_SECTION_SPECS


def ensure_master_required_keys(data: JsonDict) -> JsonDict:
    missing = [key for key in MASTER_REQUIRED_KEYS if key not in data]
    if missing:
        raise ValueError(f"Master-Taxonomie unvollstaendig: {', '.join(missing)}")
    return data


def ensure_projection_required_keys(payload: JsonDict) -> JsonDict:
    missing = [key for key in PROJECTION_REQUIRED_KEYS if key not in payload]
    if missing:
        raise ValueError(f"Projektionsdatei unvollstaendig: {', '.join(missing)}")
    return payload


def index_codes(items: list[JsonDict], kind: str) -> dict[str, JsonDict]:
    indexed: dict[str, JsonDict] = {}
    for item in items:
        code = str(item.get("code", "")).strip()
        if not code:
            raise ValueError(f"Fehlender Code in {kind}")
        indexed[code] = item
    return indexed


def materialize_codes(indexed: dict[str, JsonDict], include_codes: list[str], kind: str) -> dict[str, JsonDict]:
    materialized: dict[str, JsonDict] = {}
    missing: list[str] = []
    for code in include_codes:
        if code not in indexed:
            missing.append(code)
            continue
        materialized[code] = indexed[code]
    if missing:
        raise ValueError(f"Projektionsdatei referenziert unbekannte {kind}-Codes: {', '.join(missing)}")
    return materialized


def validate_projection_includes(master: JsonDict, payload: JsonDict) -> None:
    for section_key, include_key, _ in PROJECTION_SECTION_SPECS:
        materialize_codes(index_codes(master[section_key], section_key), list(payload.get(include_key, [])), section_key)


def require_projection_file_token(projection_id: str) -> str:
    target = str(projection_id).strip()
    if not target:
        raise ValueError("projection_id darf nicht leer sein.")
    if any(char in target for char in "\\/:*?\"<>|"):
        raise ValueError(f"projection_id enthaelt ungueltige Zeichen: {target}")
    if target == "master":
        raise ValueError("projection_id 'master' ist reserviert.")
    return target


def require_projection_template(master: JsonDict, template_id: str) -> JsonDict:
    target = str(template_id).strip()
    if not target:
        raise ValueError("template_id darf nicht leer sein.")
    for template in master.get("projection_templates", []) or []:
        current_id = str(template.get("projection_id") or template.get("id") or "").strip()
        if current_id == target:
            return template
    raise ValueError(f"Projection Template nicht gefunden: {target}")
