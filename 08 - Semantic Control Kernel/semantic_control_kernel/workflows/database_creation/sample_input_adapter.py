from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.paths import stable_hash
from semantic_control_kernel.types.adapter_results import AdapterCallResult
from semantic_control_kernel.types.database_creation import DatabaseCreationTarget
from semantic_control_kernel.workflows.database_creation.optimizer_sample_normalizer import (
    analyze_sample_input_from_optimizer_raw,
)


RAW_SAMPLE_SUFFIXES = frozenset(
    {
        ".bmp",
        ".cfg",
        ".conf",
        ".csv",
        ".doc",
        ".docx",
        ".eml",
        ".htm",
        ".html",
        ".jpeg",
        ".jpg",
        ".markdown",
        ".md",
        ".odt",
        ".pdf",
        ".png",
        ".properties",
        ".rtf",
        ".tif",
        ".tiff",
        ".toml",
        ".tsv",
        ".txt",
        ".webp",
        ".yaml",
        ".yml",
    }
)


def sample_refs_from_input(
    *,
    target: DatabaseCreationTarget,
    orchestrator_adapter: Any | None,
    workflow_run_id: str,
) -> tuple[Mapping[str, Any], ...]:
    input_root = Path(target.input_path)
    if not input_root.is_dir():
        return ()
    refs: list[Mapping[str, Any]] = []
    refs.extend(_existing_analyze_input_refs(input_root))
    for path in _raw_sample_paths(input_root):
        ref = _raw_sample_ref(
            path=path,
            input_root=input_root,
            orchestrator_adapter=orchestrator_adapter,
            workflow_run_id=workflow_run_id,
        )
        if ref is not None:
            refs.append(ref)
    return tuple(refs)


def _existing_analyze_input_refs(input_root: Path) -> list[Mapping[str, Any]]:
    refs: list[Mapping[str, Any]] = []
    for path in sorted(input_root.rglob("*.json")):
        payload = _read_json_object(path)
        if payload.get("schema_version") != "kernel.analyze_sample.input.v1":
            continue
        sample_id = _clean_text(payload.get("sample_id")) or _sample_id(path, input_root)
        payload["sample_id"] = sample_id
        refs.append({"sample_id": sample_id, "path": str(path.resolve(strict=False)), "analyze_sample_input": payload})
    return refs


def _raw_sample_paths(input_root: Path) -> tuple[Path, ...]:
    paths = []
    for path in sorted(input_root.rglob("*")):
        if path.is_file() and path.suffix.lower() in RAW_SAMPLE_SUFFIXES:
            paths.append(path)
    return tuple(paths)


def _raw_sample_ref(
    *,
    path: Path,
    input_root: Path,
    orchestrator_adapter: Any | None,
    workflow_run_id: str,
) -> Mapping[str, Any] | None:
    sample_id = _sample_id(path, input_root)
    if orchestrator_adapter is None:
        return _inspection_error_ref(sample_id, path, "Orchestrator sample inspection adapter is unavailable.")
    result = orchestrator_adapter.inspect_source_sample(
        {
            "source_document_path": str(path.resolve(strict=False)),
            "sample_label": sample_id,
            "max_excerpt_chars": 20000,
            "timeout_seconds": 600,
            "workflow_run_id": workflow_run_id,
        }
    )
    output_refs = _adapter_output_refs(result)
    if not output_refs:
        return _inspection_error_ref(sample_id, path, _adapter_error_summary(result))
    raw_paths = [str(item) for item in output_refs.get("raw_extract_paths", []) if str(item).strip()]
    raw_payloads = [_read_json_object(Path(raw_path)) for raw_path in raw_paths]
    raw_payloads = [payload for payload in raw_payloads if payload.get("schema_version") == "optimizer_raw_v2"]
    if not raw_payloads:
        return _inspection_error_ref(sample_id, path, "Optimizer sample inspection did not return optimizer_raw_v2 artifacts.")
    return {
        "sample_id": sample_id,
        "path": str(path.resolve(strict=False)),
        "analyze_sample_input": analyze_sample_input_from_optimizer_raw(
            sample_id=sample_id,
            source_path=path,
            raw_payloads=raw_payloads,
            raw_extract_paths=raw_paths,
        ),
    }


def _adapter_output_refs(result: object) -> dict[str, Any]:
    if isinstance(result, AdapterCallResult):
        payload = result.to_dict()
    elif isinstance(result, Mapping):
        payload = dict(result)
    else:
        payload = {}
    if payload.get("status") != "ok":
        return {}
    output = payload.get("output_refs")
    return dict(output) if isinstance(output, Mapping) else {}


def _adapter_error_summary(result: object) -> str:
    payload = result.to_dict() if isinstance(result, AdapterCallResult) else dict(result) if isinstance(result, Mapping) else {}
    diagnostics = payload.get("diagnostics")
    if isinstance(diagnostics, list):
        for item in diagnostics:
            if isinstance(item, Mapping):
                text = _clean_text(item.get("summary")) or _clean_text(item.get("message")) or _clean_text(item.get("code"))
                if text:
                    return text
    status = _clean_text(payload.get("status")) or "owner_error"
    return f"Orchestrator sample inspection did not return optimizer raw output ({status})."


def _inspection_error_ref(sample_id: str, path: Path, summary: str) -> Mapping[str, Any]:
    return {
        "sample_id": sample_id,
        "path": str(path.resolve(strict=False)),
        "sample_inspection_error": {
            "code": "sample_inspection_failed",
            "summary": summary,
        },
    }


def _sample_id(path: Path, input_root: Path) -> str:
    try:
        relative = path.resolve(strict=False).relative_to(input_root.resolve(strict=False)).as_posix()
    except ValueError:
        relative = path.name
    stem = re.sub(r"[^a-zA-Z0-9]+", "_", path.stem).strip("_").lower() or "sample"
    return f"{stem}_{stable_hash(relative)[:8]}"


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def _clean_text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None
