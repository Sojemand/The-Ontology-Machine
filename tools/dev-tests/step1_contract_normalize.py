from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from corpus_builder.context import ModuleContext

FIXED_TIMESTAMP = "2026-04-03T00:00:00Z"
FIXED_GENERATED_AT = "2026-04-03T00:00:00Z"


def normalize_request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(payload))
    request_root = Path(str(normalized["source"]["file_path"])).parent
    replacements = request_replacements(request_root)
    return replace_strings(normalized, replacements)


def normalize_structured_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(payload))
    source_path = Path(str(normalized["source"]["file_path"]))
    replacements = request_replacements(source_path.parent)
    normalized = replace_strings(normalized, replacements)
    normalized["processing"]["processed_at"] = FIXED_TIMESTAMP
    return normalized


def normalize_normalized_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(payload))
    normalized["processing"]["processed_at"] = FIXED_TIMESTAMP
    return normalized


def normalize_semantic_status_payload(payload: dict[str, Any], context: ModuleContext) -> dict[str, Any]:
    normalized = json.loads(json.dumps(payload))
    replacements = context_replacements(context)
    normalized = replace_strings(normalized, replacements)
    normalized["release_analysis"]["generated_at"] = FIXED_GENERATED_AT
    return normalized


def normalize_active_release_payload(payload: dict[str, Any], context: ModuleContext) -> dict[str, Any]:
    normalized = json.loads(json.dumps(payload))
    replacements = context_replacements(context)
    normalized = replace_strings(normalized, replacements)
    normalized["status"]["release_analysis"]["generated_at"] = FIXED_GENERATED_AT
    return normalized


def request_replacements(request_root: Path) -> dict[str, str]:
    return {
        str(request_root / "scan.pdf"): "${request_root}/scan.pdf",
        str(request_root / "page_assets" / "scan_pdf" / "page_001.png"): "${request_root}/page_assets/scan_pdf/page_001.png",
        str(request_root / "page_assets" / "scan_pdf" / "page_002.png"): "${request_root}/page_assets/scan_pdf/page_002.png",
    }


def context_replacements(context: ModuleContext) -> dict[str, str]:
    return {
        str(context.config_dir / "semantic_release.default.json"): "${corpus_context}/config/semantic_release.default.json",
        str(context.state_dir / "semantic_release.active.json"): "${corpus_context}/state/semantic_release.active.json",
        str(context.state_dir / "semantic_release_report.json"): "${corpus_context}/state/semantic_release_report.json",
        str(context.resolve_path("./output/test.corpus.db")): "${corpus_context}/output/test.corpus.db",
    }


def replace_strings(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: replace_strings(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [replace_strings(item, replacements) for item in value]
    if isinstance(value, str):
        return replacements.get(value, value)
    return value
