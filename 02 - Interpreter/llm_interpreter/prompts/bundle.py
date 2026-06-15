"""Prompt-bundle loading and normalization helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import atomic_text_write
from ..runtime_paths import resolve_runtime_paths
from .bundle_defaults import PROJECTION_HINT_POLICY_MD, USER_PROMPT_RULES_MD
from .contract import OUTPUT_SCHEMA, SYSTEM_PROMPT
from .schema import get_output_schema

PROMPT_BUNDLE_FILES = {
    "system_prompt_md": "system_prompt.md",
    "user_prompt_rules_md": "user_prompt_rules.md",
    "output_schema_json": "output_schema.json",
    "projection_hint_policy_md": "projection_hint_policy.md",
}

PROMPT_BUNDLE_KEYS = tuple(PROMPT_BUNDLE_FILES)


def default_prompt_bundle() -> dict[str, str]:
    return {
        "system_prompt_md": SYSTEM_PROMPT,
        "user_prompt_rules_md": USER_PROMPT_RULES_MD,
        "output_schema_json": OUTPUT_SCHEMA,
        "projection_hint_policy_md": PROJECTION_HINT_POLICY_MD,
    }


def prompt_bundle_dir(config_dir: Path | None = None) -> Path:
    base_dir = resolve_runtime_paths().config_dir if config_dir is None else config_dir
    return base_dir / "prompt_bundle"


def load_prompt_bundle(config_dir: Path | None = None) -> dict[str, str]:
    bundle_dir = prompt_bundle_dir(config_dir)
    if not bundle_dir.exists():
        return default_prompt_bundle()
    return _read_prompt_bundle(bundle_dir)


def normalize_prompt_bundle_payload(payload: dict[str, Any]) -> dict[str, str]:
    if not isinstance(payload, dict):
        raise ValueError("prompt_bundle muss ein JSON-Objekt sein.")
    missing = [key for key in PROMPT_BUNDLE_KEYS if key not in payload]
    extras = [key for key in payload if key not in PROMPT_BUNDLE_KEYS]
    if missing or extras:
        details = []
        if missing:
            details.append(f"fehlend: {', '.join(missing)}")
        if extras:
            details.append(f"unerlaubt: {', '.join(extras)}")
        raise ValueError(f"prompt_bundle hat ungueltige Felder ({'; '.join(details)}).")
    normalized = {
        key: _normalize_text_block(payload[key], label=key)
        for key in PROMPT_BUNDLE_KEYS
    }
    normalized["output_schema_json"] = _normalize_output_schema_json(normalized["output_schema_json"])
    return normalized


def _read_prompt_bundle(bundle_dir: Path) -> dict[str, str]:
    if not bundle_dir.is_dir():
        raise ValueError(f"Prompt-Bundle-Pfad ist kein Verzeichnis: {bundle_dir}")
    payload = {}
    for key, filename in PROMPT_BUNDLE_FILES.items():
        path = bundle_dir / filename
        if not path.exists():
            raise ValueError(f"Prompt-Bundle unvollstaendig: {filename} fehlt.")
        payload[key] = path.read_text(encoding="utf-8")
    payload["output_schema_json"] = _coerce_saved_output_schema_json(payload["output_schema_json"])
    normalized = normalize_prompt_bundle_payload(payload)
    schema_path = bundle_dir / PROMPT_BUNDLE_FILES["output_schema_json"]
    if schema_path.read_text(encoding="utf-8") != normalized["output_schema_json"]:
        atomic_text_write(schema_path, normalized["output_schema_json"] + "\n")
    return normalized


def _coerce_saved_output_schema_json(text: str) -> str:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"output_schema_json ist ungueltiges JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError("output_schema_json muss ein JSON-Objekt sein.")
    canonical = get_output_schema()
    return json.dumps(canonical, indent=2, ensure_ascii=False)


def _normalize_output_schema_json(text: str) -> str:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"output_schema_json ist ungueltiges JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError("output_schema_json muss ein JSON-Objekt sein.")
    canonical = get_output_schema()
    if payload != canonical:
        raise ValueError("output_schema_json muss exakt dem kanonischen Output-Schema entsprechen.")
    return json.dumps(canonical, indent=2, ensure_ascii=False)


def _normalize_text_block(value: object, *, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} muss ein String sein.")
    text = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        raise ValueError(f"{label} darf nicht leer sein.")
    return text


__all__ = [
    "PROMPT_BUNDLE_FILES",
    "PROMPT_BUNDLE_KEYS",
    "default_prompt_bundle",
    "load_prompt_bundle",
    "normalize_prompt_bundle_payload",
    "prompt_bundle_dir",
]
