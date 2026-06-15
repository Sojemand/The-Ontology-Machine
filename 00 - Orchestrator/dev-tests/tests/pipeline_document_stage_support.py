from __future__ import annotations

import hashlib
import json
from pathlib import Path


_VISION_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif", ".webp"}


def build_raw_payload(
    optimizer_profile: str,
    raw_doc: dict[str, object],
    page_path: Path,
    *,
    page_number: int = 1,
) -> dict[str, object]:
    page_count = int(raw_doc.get("page_count", 1) or 1)
    source = {
        "ingest_id": str(raw_doc.get("ingest_id") or ""),
        "file_name": str(raw_doc.get("file_name") or raw_doc.get("filename") or ""),
        "file_path": str(raw_doc.get("file_path") or raw_doc.get("path") or ""),
        "relative_path": str(raw_doc.get("path") or ""),
        "file_ext": str(raw_doc.get("file_ext") or ""),
        "content_hash": str(raw_doc.get("content_hash") or ""),
        "page_count": page_count,
    }
    payload = {
        "schema_version": "optimizer_raw_v2",
        "optimizer_profile": optimizer_profile,
        "source": source,
        "extraction": {"plugin_name": "fake", "plugin_version": "1.0.0", "processing_time_ms": 1},
        "metadata": {},
        "context": {
            "page_number": page_number,
            "document_page_count": page_count,
            "source_document_path": str(raw_doc.get("path") or ""),
            "page_source_path": f"{raw_doc.get('path') or ''}::page={page_number:03d}-of-{page_count:03d}",
        },
        "ocr_reference": {"blocks": []},
    }
    if optimizer_profile == "vision":
        payload["ocr_reference"]["blocks"] = [
            {
                "id": f"page{page_number}_para_0",
                "type": "paragraph",
                "value": "hello",
                "value_type": "text",
                "position": {"page": page_number, "paragraph_index": 0},
            }
        ]
        return payload
    payload["ocr_reference"]["blocks"] = [
        {
            "id": f"page{page_number}_para_0",
            "type": "paragraph",
            "value": "hello",
            "value_type": "text",
            "position": {"page": page_number, "paragraph_index": 0},
        }
    ]
    return payload


def optimizer_profile_for_source(source_path: Path, *, runtime_policy_path: Path | None) -> str:
    if runtime_policy_path is not None:
        return "vision"
    return "vision" if source_path.suffix.lower() in _VISION_SUFFIXES else "file"


def default_report_name(structured_path: Path) -> str:
    payload = json.loads(structured_path.read_text(encoding="utf-8"))
    processing = payload.get("processing", {}) if isinstance(payload, dict) else {}
    profile = str(processing.get("interpreter_profile", "vision")).strip() or "vision"
    suffix = ".files_validation_report.json" if profile == "file" else ".vision_validation_report.json"
    if structured_path.name.endswith(".structured.json"):
        return structured_path.name[: -len(".structured.json")] + suffix
    return f"{structured_path.stem}{suffix}"


def sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"

