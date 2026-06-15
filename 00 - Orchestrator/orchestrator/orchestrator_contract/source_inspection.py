"""Source document inspection helpers for the orchestrator contract."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4

from ..debug_host import workflow as debug_workflow
from .source_inspection_payload import inspection_signals, summarize_raw_payload
from .source_inspection_runtime import (
    cleanup_old_inspections,
    read_json,
    resolved_outputs,
    safe_inspection_filename,
    source_inspection_modules,
    wait_for_debug_session,
)
from .source_inspection_text import excerpt_chunks, flatten, join_unique, keyword_markers, limit_unique

DEFAULT_INSPECTION_MAX_EXCERPT_CHARS = 6000
DEFAULT_INSPECTION_TIMEOUT_SECONDS = 120
DEFAULT_INSPECTION_CLEANUP_DAYS = 1
INSPECTION_MAX_EXCERPT_CHAR_LIMIT = 20000
INSPECTION_TIMEOUT_LIMIT_SECONDS = 600
_SOURCE_INSPECTION_DIR = "source_inspections"


def inspect_source_document_sample_action(command: dict[str, Any], *, root: Path) -> dict:
    source_path = Path(str(command["source_document_path"])).expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")
    if not source_path.is_file():
        raise ValueError(f"Source document must be a file: {source_path}")

    max_excerpt_chars = min(
        int(command.get("max_excerpt_chars") or DEFAULT_INSPECTION_MAX_EXCERPT_CHARS),
        INSPECTION_MAX_EXCERPT_CHAR_LIMIT,
    )
    timeout_seconds = min(
        int(command.get("timeout_seconds") or DEFAULT_INSPECTION_TIMEOUT_SECONDS),
        INSPECTION_TIMEOUT_LIMIT_SECONDS,
    )
    cleanup_days = int(command.get("cleanup_days", DEFAULT_INSPECTION_CLEANUP_DAYS))
    inspection_base = Path(root) / "state" / _SOURCE_INSPECTION_DIR
    cleanup_old_inspections(inspection_base, older_than_days=cleanup_days)
    modules = source_inspection_modules(Path(root))

    inspection_id = f"inspect_{uuid4().hex[:12]}"
    inspection_root = inspection_base / inspection_id
    input_root = inspection_root / "Input"
    input_root.mkdir(parents=True, exist_ok=True)
    input_copy = input_root / safe_inspection_filename(source_path.name, parent=input_root)
    shutil.copy2(source_path, input_copy)

    session = debug_workflow.start(
        "optimizer",
        "single",
        input_root,
        source_path=input_copy.name,
        state_root=inspection_root,
        session_id="optimizer_sample",
        options={"worker_count": 1},
        modules=modules,
    )
    session = wait_for_debug_session(session, timeout_seconds=timeout_seconds, modules=modules)
    result = session.result
    if result is None:
        raise RuntimeError("Document inspection ended without a result.")
    if result.status != "ok":
        raise RuntimeError(result.error or result.summary or "Document inspection failed.")

    raw_extract_paths = resolved_outputs(session.session_root, result.outputs.get("raw_extracts", []))
    page_image_paths = resolved_outputs(session.session_root, result.outputs.get("page_images", []))
    raw_payloads = [read_json(path) for path in raw_extract_paths if path.exists()]
    summaries = [summarize_raw_payload(payload) for payload in raw_payloads]
    combined_text = join_unique(summary["text"] for summary in summaries)
    excerpts, truncated = excerpt_chunks(combined_text, max_chars=max_excerpt_chars)

    raw_refs = [str(path) for path in raw_extract_paths]
    page_refs = [str(path) for path in page_image_paths]
    return {
        "status": "ok",
        "inspection_id": inspection_id,
        "inspection_folder": str(inspection_root),
        "source_document_path": str(source_path),
        "input_copy_path": str(input_copy),
        "sample_label": str(command.get("sample_label") or source_path.stem),
        "signals": inspection_signals(source_path, raw_payloads, raw_extract_paths, page_image_paths),
        "content_hints": {
            "headings": limit_unique(flatten(summary["headings"] for summary in summaries), limit=20),
            "field_like_phrases": limit_unique(flatten(summary["field_like_phrases"] for summary in summaries), limit=30),
            "candidate_markers": keyword_markers(combined_text, limit=30),
        },
        "excerpt": {
            "chars_returned": sum(len(item) for item in excerpts),
            "truncated": truncated,
            "chunks": excerpts,
        },
        "raw_extract_paths": raw_refs,
        "page_image_paths": page_refs,
        "output_refs": {
            "inspection_folder": str(inspection_root),
            "input_copy_path": str(input_copy),
            "raw_extract_paths": raw_refs,
            "page_image_paths": page_refs,
        },
        "workflow_guidance": [
            "Nutze diese Auszuege, um dem User ein passendes Spezialarchiv mit Dokumentprofilen und Feldern vorzuschlagen.",
            "Erklaere dem User die vorgeschlagenen Felder in Alltagssprache, bevor du create_projection_draft oder Aktivierungs-Tools nutzt.",
            "Diese Inspektion veraendert keine Datenbank und aktiviert kein Extraktionspaket.",
        ],
    }
