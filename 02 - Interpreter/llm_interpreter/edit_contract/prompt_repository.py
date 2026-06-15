"""Prompt-bundle and preview helpers for the Interpreter edit contract."""
from __future__ import annotations

from ..prompts.bundle import PROMPT_BUNDLE_FILES, load_prompt_bundle, normalize_prompt_bundle_payload
from ..prompts.schema import get_output_schema, get_persisted_output_schema
from .files import atomic_text_write


def read_prompt_bundle(paths) -> dict[str, str]:
    return load_prompt_bundle(paths.config_dir)


def write_prompt_bundle(paths, payload: dict) -> dict[str, str]:
    normalized = normalize_prompt_bundle_payload(payload)
    bundle_dir = paths.config_dir / "prompt_bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    for key, filename in PROMPT_BUNDLE_FILES.items():
        atomic_text_write(bundle_dir / filename, normalized[key] + "\n")
    return load_prompt_bundle(paths.config_dir)


def read_output_contract_preview() -> dict:
    return {
        "model_output_schema": get_output_schema(),
        "persisted_output_schema": get_persisted_output_schema(),
        "editable_extension_zones": ["context", "content.fields", "content.rows[*]", "content.segments[*]"],
        "projection_catalog_required": True,
        "review_rules": [
            "projection_catalog is required on input",
            "processing.interpreter_profile must stay profile-consistent with the request",
            "ocr/vlm guideline is secondary to the document reading",
            "projection_hint is advisory and may be omitted",
            "values in context, content.fields, and content.rows must appear in content.free_text",
            "segment text should be directly recoverable from content.free_text",
            "content.segments may carry unit_kind and function as local semantic anchors",
        ],
    }


__all__ = ["read_output_contract_preview", "read_prompt_bundle", "write_prompt_bundle"]
