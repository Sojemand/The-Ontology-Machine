from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping


def _release_ref_from_create_output(output: Mapping[str, Any]) -> dict[str, Any]:
    nested = output.get("release_ref")
    release_ref = dict(nested) if isinstance(nested, Mapping) else dict(output)
    release_id = str(release_ref.get("release_id") or output.get("release_id") or output.get("semantic_release_id") or "").strip()
    release_version = str(release_ref.get("release_version") or output.get("release_version") or output.get("semantic_release_version") or "").strip()
    release_fingerprint = str(release_ref.get("release_fingerprint") or output.get("release_fingerprint") or "").strip()
    if release_id:
        release_ref["release_id"] = release_id
    if release_version:
        release_ref["release_version"] = release_version
    if release_fingerprint:
        release_ref["release_fingerprint"] = release_fingerprint
    return release_ref


def _release_ref_from_write_output(output: Mapping[str, Any], *, fallback: Mapping[str, Any]) -> dict[str, Any]:
    release_ref = dict(fallback)
    nested = output.get("release_ref")
    if isinstance(nested, Mapping):
        for key, value in nested.items():
            if value not in ("", None, [], {}):
                release_ref[key] = value
    for key in ("release_id", "release_version", "release_fingerprint", "runtime_locale"):
        value = output.get(key)
        if value:
            release_ref[key] = str(value)
    if output.get("fingerprint"):
        release_ref["release_fingerprint"] = str(output["fingerprint"])
    for key in ("taxonomy_ref", "projection_refs"):
        value = output.get(key)
        if value not in ("", None, [], {}):
            release_ref[key] = value
    return release_ref


def _release_path_from_write_output(output: Mapping[str, Any], *, fallback: str) -> str:
    value = str(output.get("release_path") or output.get("output_path") or fallback).strip()
    if value and not value.casefold().endswith(".json"):
        return str(Path(value) / "release.json")
    return value
