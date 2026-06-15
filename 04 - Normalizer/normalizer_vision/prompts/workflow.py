"""Workflow stage for prompt-text and message assembly."""
from __future__ import annotations

import json
from typing import Any

from ..taxonomy import TaxonomyProfile
from .contract import SYSTEM_PROMPT, USER_QUALITY_RULES, USER_TASK_INTRO, build_default_output_schema_template_text, get_output_schema_text, get_prompt
from .dynamic_schema import build_dynamic_output_contract
from .promotion_contract import promotion_contract_lines
from .types import PromptBundle


def build_user_prompt_text(
    structured_doc: dict[str, Any],
    profile: TaxonomyProfile,
    prompt_bundle: PromptBundle | None = None,
) -> str:
    raw_classification = structured_doc.get("classification", {}) or {}
    task_intro = _block_lines(get_prompt("user_task_intro", USER_TASK_INTRO, prompt_bundle))
    quality_rules = _block_lines(get_prompt("user_quality_rules", USER_QUALITY_RULES, prompt_bundle))
    lines = [
        f"Active taxonomy profile: {profile.projection_id}",
        "",
        *task_intro,
        "",
        "Allowed document_type codes:",
        _format_codes(profile.document_types),
        "",
        "Allowed category codes:",
        _format_codes(profile.categories),
        "",
        "Allowed subcategory codes:",
        _format_codes(profile.subcategories),
        "",
        "Allowed field_codes:",
        _format_codes(profile.field_codes),
        "",
        "Allowed row_types:",
        _format_codes(profile.row_types),
        "",
        "Allowed cell_codes:",
        _format_codes(profile.cell_codes),
        "",
        *promotion_contract_lines(profile),
        "",
        *quality_rules,
        "",
        f"Raw classification hint: {json.dumps(raw_classification, ensure_ascii=False)}",
        "",
        "Input structured.json:",
        json.dumps(structured_doc, indent=2, ensure_ascii=False),
        "",
        "Return the result exactly in this target schema / example contract:",
        _target_schema_text(profile, prompt_bundle),
    ]
    return "\n".join(lines)


def build_messages(
    structured_doc: dict[str, Any],
    profile: TaxonomyProfile,
    prompt_bundle: PromptBundle | None = None,
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": get_prompt("system_prompt", SYSTEM_PROMPT, prompt_bundle)},
        {"role": "user", "content": build_user_prompt_text(structured_doc, profile, prompt_bundle)},
    ]


def _format_codes(items: dict[str, dict[str, Any]]) -> str:
    return "\n".join(f"- {code}: {item.get('description', '')}" for code, item in items.items())


def _target_schema_text(profile: TaxonomyProfile, prompt_bundle: PromptBundle | None) -> str:
    if prompt_bundle is not None:
        custom = prompt_bundle.prompts.get("output_schema")
        if custom and custom.strip() != build_default_output_schema_template_text().strip():
            return get_output_schema_text(profile.projection_id, prompt_bundle)
    return build_dynamic_output_contract(profile)


def _block_lines(text: str) -> list[str]:
    return str(text).rstrip("\n").splitlines()


__all__ = ["build_messages", "build_user_prompt_text"]
