"""Workflow stage for prompt-text and vision-message assembly."""
from __future__ import annotations

import base64
import json
from typing import Any

from ..profile_policy import request_has_explicit_profile, request_profile
from ..models.types import InterpreterConfig, VISION_IMAGE_DETAIL
from .adapter import load_page_assets
from .bundle import load_prompt_bundle
from .bundle_defaults import resolve_user_prompt_rules
from .contract import resolve_system_prompt
from .mode_policy import request_is_scan
from .projection_hint import build_projection_catalog_block
from .types import LoadedPageAsset

def build_user_prompt_text(
    request: dict[str, Any],
    config: InterpreterConfig,
    *,
    prompt_bundle: dict[str, str] | None = None,
) -> str:
    bundle = load_prompt_bundle() if prompt_bundle is None else prompt_bundle
    source = request.get("source", {}) or {}
    context = request.get("context", {}) or {}
    file_profile = _effective_profile(request, config) == "file"
    is_scan = request_is_scan(request)
    lines = _request_header_lines(source, context, file_profile=file_profile)
    if context:
        lines.extend(["", "Context:"])
        for key, value in context.items():
            lines.append(f"- {key}: {value}")
    ocr_blocks_block = _render_ocr_blocks_block(request, file_profile=file_profile)
    if ocr_blocks_block:
        lines.extend(["", ocr_blocks_block])
    lines.extend(["", bundle["projection_hint_policy_md"], "", build_projection_catalog_block(request)])
    user_prompt_rules = resolve_user_prompt_rules(
        is_file_profile=file_profile,
        is_scan=is_scan,
        configured_text=bundle.get("user_prompt_rules_md"),
    )
    lines.extend(["", user_prompt_rules, "", _schema_instruction(file_profile), bundle["output_schema_json"]])
    return "\n".join(lines)

def build_vision_messages(
    request: dict[str, Any],
    config: InterpreterConfig,
    *,
    page_assets: list[LoadedPageAsset] | None = None,
) -> list[dict[str, Any]]:
    prompt_bundle = load_prompt_bundle()
    pages = page_assets or load_page_assets(request)
    file_profile = _effective_profile(request, config) == "file"
    system_prompt = resolve_system_prompt(
        is_file_profile=file_profile,
        is_scan=request_is_scan(request),
        configured_text=prompt_bundle.get("system_prompt_md"),
    )
    content_blocks: list[dict[str, Any]] = [
        {"type": "text", "text": build_user_prompt_text(request, config, prompt_bundle=prompt_bundle)}
    ]
    for page in pages:
        encoded = base64.b64encode(page["bytes"]).decode("ascii")
        content_blocks.append(
            {
                "type": "input_image",
                "page": page.get("page"),
                "image_url": f"data:{page['media_type']};base64,{encoded}",
                "detail": _request_image_detail(request),
            }
        )
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": content_blocks}]
    return messages

def build_message_snapshot(messages: list[dict[str, Any]]) -> dict[str, Any]:
    system_prompt = messages[0].get("content", "") if messages else ""
    system_prompt = system_prompt if isinstance(system_prompt, str) else ""
    user_blocks = _user_blocks(messages)
    user_block_types = [str(block.get("type") or "").strip() for block in user_blocks if block.get("type")]
    return {
        "system_prompt_preview": system_prompt[:400],
        "user_block_types": user_block_types,
        "image_block_count": sum(1 for block_type in user_block_types if block_type == "input_image"),
        "user_text_chars": sum(len(str(block.get("text") or "")) for block in user_blocks if block.get("type") == "text"),
        "image_chars_total": sum(len(str(block.get("image_url") or "")) for block in user_blocks if block.get("type") == "input_image"),
    }


def _request_header_lines(source: dict[str, Any], context: dict[str, Any], *, file_profile: bool) -> list[str]:
    labels = ("File", "Type hint", "Source language", "Pages")
    lines = [
        f"{labels[0]}: {source.get('file_name', 'unknown')}",
        f"{labels[1]}: {source.get('document_type', 'unknown')}",
        f"{labels[2]}: {source.get('language', 'unknown')}",
        f"{labels[3]}: {source.get('page_count', 0)}",
    ]
    page_number = context.get("page_number")
    page_count = context.get("document_page_count")
    if isinstance(page_number, int) and page_number > 0 and isinstance(page_count, int) and page_count > 0:
        lines.append(f"Visible page: {page_number} of {page_count}")
    return lines

def _effective_profile(request: dict[str, Any], config: InterpreterConfig) -> str:
    return request_profile(request) if request_has_explicit_profile(request) else config.interpreter_profile


def _schema_instruction(file_profile: bool) -> str:
    return "Return the result exactly in the structured schema:"


def _render_ocr_blocks_block(request: dict[str, Any], *, file_profile: bool) -> str:
    reference = request.get("ocr_reference")
    if not isinstance(reference, dict):
        return ""
    blocks = reference.get("blocks")
    if not isinstance(blocks, list):
        return ""
    rendered = [
        json.dumps(_prompt_block_view(block), ensure_ascii=False)
        for block in blocks
        if isinstance(block, dict) and str(block.get("value", "")).strip()
    ]
    if not rendered:
        return ""
    heading = "OCR raw blocks in source order:"
    return "\n".join([heading, *[f"- {line}" for line in rendered]])


def _prompt_block_view(block: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": block.get("id"),
        "type": block.get("type"),
        "value": block.get("value"),
        "value_type": block.get("value_type"),
    }
    for key in ("layout_label", "confidence", "position", "formatting", "origin"):
        value = block.get(key)
        if value in (None, "", [], {}):
            continue
        payload[key] = value
    return payload


def _user_blocks(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(messages) <= 1:
        return []
    content = messages[1].get("content", [])
    return [block for block in content if isinstance(block, dict)] if isinstance(content, list) else []


def _request_image_detail(request: dict[str, Any]) -> str:
    detail = str(request.get("image_detail") or "").strip().lower()
    return detail if detail in {"high", "low", "auto"} else VISION_IMAGE_DETAIL


__all__ = ["build_message_snapshot", "build_user_prompt_text", "build_vision_messages"]
