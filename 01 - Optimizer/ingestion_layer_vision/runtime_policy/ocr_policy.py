"""Resolution helpers for the runtime OCR policy."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from .types import RuntimeOcrPolicy

INTERPRETER_PAGE_ASSET_DPI = 150
_LLM_OCR_PLUGIN = "optimizer-llm-ocr"

_LEGACY_DEFAULTS: dict[str, Any] = {
    "profile_id": "legacy_defaults_v1",
    "scan": {"min_chars_per_page": 50, "use_has_images": True},
    "vision_route": {"images_always_vision": True, "pdf_scans_use_vision": True},
    "ocr_plugin": {"preferred_plugin": _LLM_OCR_PLUGIN, "force_backup_on_scan": True},
    "render": {
        "page_image_dpi": INTERPRETER_PAGE_ASSET_DPI,
        "page_image_quality": 95,
        "serializer_quality_mode": "best_quality",
        "ocr_render_dpi": 450,
    },
}


def profile_id(policy: RuntimeOcrPolicy | None) -> str:
    return str(_defaults(policy).get("profile_id") or "")


def scan_policy(policy: RuntimeOcrPolicy | None) -> dict[str, Any]:
    return dict(_section(policy, "scan"))


def vision_route_policy(policy: RuntimeOcrPolicy | None) -> dict[str, Any]:
    return dict(_section(policy, "vision_route"))


def preferred_plugin(policy: RuntimeOcrPolicy | None) -> str:
    del policy
    return _LLM_OCR_PLUGIN


def force_backup_on_scan(policy: RuntimeOcrPolicy | None) -> bool:
    return bool(_section(policy, "ocr_plugin").get("force_backup_on_scan", True))


def page_image_render_policy(policy: RuntimeOcrPolicy | None) -> dict[str, int]:
    render = _section(policy, "render")
    return {
        "dpi": INTERPRETER_PAGE_ASSET_DPI,
        "quality": int(render.get("page_image_quality", 95) or 95),
    }


def worker_startup_config(policy: RuntimeOcrPolicy | None) -> dict[str, Any]:
    del policy
    return {
        "engine": "llm",
        "plugin_name": _LLM_OCR_PLUGIN,
    }


def request_config(policy: RuntimeOcrPolicy | None) -> dict[str, Any]:
    render = _section(policy, "render")
    return {
        **worker_startup_config(policy),
        "quality_mode": str(render.get("serializer_quality_mode") or "best_quality"),
        "render_dpi": int(render.get("ocr_render_dpi", 450) or 450),
    }


def startup_config_signature(policy: RuntimeOcrPolicy | None) -> str:
    payload = json.dumps(worker_startup_config(policy), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def build_trace_fields(policy: RuntimeOcrPolicy) -> dict[str, str]:
    scan = scan_policy(policy)
    render = _section(policy, "render")
    return {
        "ocr_policy_version": policy.policy_version,
        "ocr_policy_source_mode": policy.source_mode,
        "ocr_profile_id": profile_id(policy),
        "ocr_scan_threshold": str(scan.get("min_chars_per_page", 50)),
        "ocr_preferred_plugin": preferred_plugin(policy),
        "ocr_render_profile": _render_profile(render),
        "ocr_engine": "llm",
        "ocr_startup_config_signature": startup_config_signature(policy),
    }


def normalize_page_image_render_defaults(defaults: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(defaults)
    render = normalized.get("render")
    render = dict(render) if isinstance(render, dict) else {}
    render["page_image_dpi"] = INTERPRETER_PAGE_ASSET_DPI
    normalized["render"] = render
    return normalized


def _defaults(policy: RuntimeOcrPolicy | None) -> dict[str, Any]:
    defaults = getattr(policy, "defaults", None)
    return normalize_page_image_render_defaults(defaults) if isinstance(defaults, dict) else _LEGACY_DEFAULTS


def _section(policy: RuntimeOcrPolicy | None, name: str) -> dict[str, Any]:
    section = _defaults(policy).get(name)
    return section if isinstance(section, dict) else {}


def _render_profile(render: dict[str, Any]) -> str:
    return "page{0}_q{1}_{2}_ocr{3}".format(
        INTERPRETER_PAGE_ASSET_DPI,
        render.get("page_image_quality", 95),
        render.get("serializer_quality_mode", "best_quality"),
        render.get("ocr_render_dpi", 450),
    )
