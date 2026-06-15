"""Path-stable surface for prompt, schema, asset, and debug helpers."""
from __future__ import annotations

from .adapter import detect_image_media_type, load_page_assets, resolve_page_media_type
from .bundle import load_prompt_bundle
from .contract import OUTPUT_SCHEMA, SYSTEM_PROMPT
from .debug import describe_page_assets
from .schema import get_output_schema, get_persisted_output_schema
from .types import MODEL_OUTPUT_TEMPLATE, OUTPUT_TEMPLATE
from .workflow import build_message_snapshot, build_user_prompt_text, build_vision_messages

__all__ = [
    "MODEL_OUTPUT_TEMPLATE",
    "OUTPUT_SCHEMA",
    "OUTPUT_TEMPLATE",
    "SYSTEM_PROMPT",
    "build_message_snapshot",
    "build_user_prompt_text",
    "build_vision_messages",
    "describe_page_assets",
    "detect_image_media_type",
    "get_output_schema",
    "get_persisted_output_schema",
    "load_prompt_bundle",
    "load_page_assets",
    "resolve_page_media_type",
]
