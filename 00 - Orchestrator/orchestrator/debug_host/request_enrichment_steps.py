"""Request-enrichment helpers for debug-host sessions."""

from __future__ import annotations

import json
from pathlib import Path

from .. import policy_store
from ..integrations.projection_catalog import load_normalizer_projection_catalog
from ..pipeline import request_enrichment
from . import polling
from .types import DebugResult


def build_request_outputs(session, *, modules, prior: DebugResult, module_key: str) -> list[str]:
    raw_items = [str(item) for item in prior.outputs.get("raw_extracts", []) if str(item).strip()]
    if not raw_items:
        raise ValueError("raw_extracts are missing after the Optimizer.")
    raw_items = _preferred_file_raw_items(session, raw_items)
    projection_catalog = _load_debug_projection_catalog(modules)
    page_items = _page_items(prior)
    outputs: list[str] = []
    source_target = session.request.resolved_source_path if session.request.mode == "single" else None
    for raw_item in raw_items:
        raw_path = polling.resolve_output_path(session.session_root, raw_item)
        page_paths = _page_paths_for_raw(session, raw_item, page_items=page_items, raw_count=len(raw_items))
        target = _request_target_for_raw(session, raw_item)
        interpreter_profile = _raw_interpreter_profile(raw_path)
        request_enrichment.build_working_request(
            modules,
            interpreter_profile=interpreter_profile,
            module_key=module_key,
            raw_path=raw_path,
            request_path=target,
            working_source_path=source_target,
            working_page_paths=page_paths,
            projection_catalog=projection_catalog,
        )
        outputs.extend(polling.relative_path(session.session_root, path) for path in [target])
    return outputs


def _preferred_file_raw_items(session, raw_items: list[str]) -> list[str]:
    grouped: dict[str, dict[str, list[str]]] = {}
    order: list[str] = []
    for raw_item in raw_items:
        raw_path = polling.resolve_output_path(session.session_root, raw_item)
        payload = _load_raw_payload_safely(raw_path)
        key = _file_raw_group_key(payload, raw_item)
        if key not in grouped:
            grouped[key] = {"document": [], "page": []}
            order.append(key)
        bucket = "page" if _is_page_scoped_file_raw(payload) else "document"
        grouped[key][bucket].append(raw_item)
    selected: list[str] = []
    for key in order:
        items = grouped[key]
        selected.extend(items["document"] or items["page"])
    return selected


def _page_items(prior: DebugResult) -> list[str]:
    items: list[str] = []
    for item in prior.outputs.get("page_assets", []):
        text = str(item).strip()
        if text and text not in items:
            items.append(text)
    return items


def _load_raw_payload_safely(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _raw_interpreter_profile(path: Path) -> str:
    payload = _load_raw_payload_safely(path)
    profile = str(payload.get("optimizer_profile", "")).strip().lower()
    return profile if profile in {"vision", "file"} else "vision"


def _file_raw_group_key(payload: dict[str, object], fallback: str) -> str:
    doc = _raw_mapping(payload, "source", "doc")
    ctx = _raw_mapping(payload, "context", "ctx")
    for value in (
        ctx.get("source_document_path"),
        doc.get("source_document_path"),
        doc.get("file_name"),
        doc.get("file_path"),
    ):
        text = str(value or "").strip()
        if text:
            return text
    return fallback


def _is_page_scoped_file_raw(payload: dict[str, object]) -> bool:
    doc = _raw_mapping(payload, "source", "doc")
    ctx = _raw_mapping(payload, "context", "ctx")
    for value in (ctx.get("page_number"), doc.get("page_number")):
        if isinstance(value, int) and value > 0:
            return True
    return False


def _raw_mapping(payload: dict[str, object], preferred_key: str, legacy_key: str) -> dict[str, object]:
    value = payload.get(preferred_key)
    if isinstance(value, dict):
        return value
    value = payload.get(legacy_key)
    return value if isinstance(value, dict) else {}


def _load_debug_projection_catalog(modules) -> dict[str, object]:
    catalog = load_normalizer_projection_catalog(modules)
    if catalog is None:
        raise ValueError("projection_catalog could not be loaded for the debug/admin path.")
    return catalog


def _request_target_for_raw(session, raw_item: str):
    relative_target = _single_request_relative_target(session)
    if relative_target is None:
        relative_target = _raw_relative_target(session, raw_item)
    return session.output_root / policy_store.publication_name("requests") / relative_target / policy_store.request_file_name("interpreter_request")


def _single_request_relative_target(session):
    logical = str(session.request.logical_source_path or "").strip()
    if session.request.mode != "single" or not logical:
        return None
    return _sanitize_relative_target(Path(logical))


def _raw_relative_target(session, raw_item: str):
    relative = _relative_to_output_root(session, polling.resolve_output_path(session.session_root, raw_item))
    if relative.parts[:1] == (policy_store.publication_name("raw_extracts"),):
        relative = Path(*relative.parts[1:])
    raw_text = relative.as_posix()
    if raw_text.endswith(".raw.json"):
        raw_text = raw_text[: -len(".raw.json")]
    target = Path(raw_text) if raw_text else Path(relative.stem or "document")
    return _sanitize_relative_target(target)


def _page_paths_for_raw(session, raw_item: str, *, page_items: list[str], raw_count: int) -> tuple[Path, ...]:
    prefixes = _page_prefixes_for_raw(session, raw_item)
    page_paths = [
        polling.resolve_output_path(session.session_root, item)
        for item in page_items
        if any(_path_has_prefix(_relative_to_output_root(session, polling.resolve_output_path(session.session_root, item)), prefix) for prefix in prefixes)
    ]
    if not page_paths and raw_count == 1:
        return tuple(polling.resolve_output_path(session.session_root, item) for item in page_items)
    return tuple(page_paths)


def _page_prefixes_for_raw(session, raw_item: str) -> tuple[Path, ...]:
    raw_relative = _raw_relative_target(session, raw_item)
    root = Path("page_assets")
    prefixes = [root / raw_relative]
    if raw_relative.suffix:
        prefixes.append((root / raw_relative).with_name(raw_relative.stem))
    deduped: list[Path] = []
    for prefix in prefixes:
        if prefix not in deduped:
            deduped.append(prefix)
    return tuple(deduped)


def _relative_to_output_root(session, path: Path) -> Path:
    try:
        return path.relative_to(session.output_root)
    except ValueError:
        return Path(path.name)


def _path_has_prefix(path: Path, prefix: Path) -> bool:
    return path.parts[: len(prefix.parts)] == prefix.parts


def _sanitize_relative_target(target: Path) -> Path:
    sanitized_parts = [_sanitize_path_part(part) for part in target.parts if str(part).strip()]
    return Path(*sanitized_parts) if sanitized_parts else Path("document")


def _sanitize_path_part(part: str) -> str:
    sanitized = str(part).rstrip(" .")
    return sanitized or "_"
