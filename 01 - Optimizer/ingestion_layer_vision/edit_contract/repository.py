"""Owner-local read/write helpers for edit-contract surfaces."""
from __future__ import annotations

import json
from pathlib import Path


def read_debug_capabilities(module_root: Path) -> dict:
    manifest = json.loads((module_root / "module-manifest.json").read_text(encoding="utf-8"))
    return {
        "module_key": str(manifest.get("module_key") or ""),
        "display_name": str(manifest.get("display_name") or ""),
        "capabilities": dict(manifest.get("debug_surface") or {}),
        "operation_links": _operation_links(manifest),
    }


def read_output_contract_preview(module_root: Path) -> dict:
    manifest = json.loads((module_root / "module-manifest.json").read_text(encoding="utf-8"))
    profiles = manifest.get("profiles") if isinstance(manifest.get("profiles"), dict) else {}
    return {
        "schema_version": "optimizer_raw_v2",
        "profile_contract": {
            "public_slot": str(profiles.get("public_slot") or "optimizer"),
            "selector_field": str(profiles.get("selector_field") or "optimizer_profile"),
            "profiles": ["vision", "file"],
        },
        "persistent_raw_sections": [
            "schema_version",
            "optimizer_profile",
            "source",
            "extraction",
            "metadata",
            "context",
            "ocr_reference.blocks",
        ],
        "extract_response_paths": [
            "document_raw_path",
            "page_raw_paths",
            "page_asset_paths",
        ],
        "page_asset_policy": {
            "response_only": True,
            "persistent_raw": False,
            "purpose": "working paths for the next Interpreter run",
        },
        "llm_ocr_runtime": {
            "dependency": "optimizer_ocr",
            "env_prefix": "OPTIMIZER_OCR_",
            "owner": "orchestrator",
            "local_ocr_plugins": False,
            "secrets_persisted_by_optimizer": False,
        },
        "non_goals": [
            "no local ruleset or override authoring",
            "no projection-catalog authoring",
            "no provider/model/secret editing inside the Optimizer slot",
            "no retroactive rewrite of existing raw extracts",
        ],
    }


def _operation_links(manifest: dict) -> list[dict[str, str]]:
    return [
        {
            "action": action,
            "label": action.replace("_", " ").title(),
            "contract_module": str(manifest.get("contract_module") or ""),
        }
        for action in manifest.get("actions", [])
        if isinstance(action, str) and action.strip()
    ]
