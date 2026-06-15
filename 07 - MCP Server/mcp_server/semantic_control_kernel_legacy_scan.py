from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .semantic_control_kernel_legacy_constants import (
    GENERATED_DIR_NAMES,
    LEGACY_STATE_DIR,
    REQUIRED_OLD_SYMBOLS,
    REQUIRED_SCAN_ROOTS,
    TEXT_LIKE_SUFFIXES,
)
from .semantic_control_kernel_legacy_items import item, item_for, synthetic_required_symbol_item


def build_legacy_inventory(module_root: Path | None = None) -> dict[str, Any]:
    root = (module_root or Path(__file__).resolve().parents[1]).resolve(strict=False)
    items = _scan_legacy_items(root)
    seen_symbols = {symbol for entry in items for symbol in entry["legacy_symbols"]}
    missing_symbols = [symbol for symbol in REQUIRED_OLD_SYMBOLS if symbol not in seen_symbols]
    if missing_symbols:
        items.append(synthetic_required_symbol_item(missing_symbols))
    return {
        "schema_version": "mcp.phase14_legacy_cleanup_inventory.v1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "generated_by": "semantic_control_kernel_legacy_inventory",
        "source_module": "../07 - MCP Server",
        "cutover_phase": 14,
        "items": items,
        "counts": _counts(items),
    }


def write_legacy_inventory(module_root: Path | None = None) -> Path:
    root = (module_root or Path(__file__).resolve().parents[1]).resolve(strict=False)
    payload = build_legacy_inventory(root)
    target = root / "migration" / "phase14_legacy_cleanup_inventory.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def _scan_legacy_items(root: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for relative in REQUIRED_SCAN_ROOTS:
        path = root / relative
        if path.is_dir():
            items.extend(_directory_items(root, path, relative))
        elif path.exists() and should_scan_file(path):
            matches = matched_symbols(path)
            if matches:
                items.append(item_for(root, path, matches))
    return items


def _directory_items(root: Path, path: Path, relative: str) -> list[dict[str, Any]]:
    if relative == LEGACY_STATE_DIR:
        matches = directory_symbol_summary(path)
        if not matches:
            return []
        return [
            item(
                LEGACY_STATE_DIR,
                "state_path",
                matches,
                "legacy_runtime_payload",
                "hidden",
                "archive_or_ignore_state",
                15,
                "Legacy Kernel runtime state remains on disk for audit only.",
                None,
            )
        ]
    return [
        item_for(root, file_path, matches)
        for file_path in sorted(candidate for candidate in path.rglob("*") if should_scan_file(candidate))
        if (matches := matched_symbols(file_path))
    ]


def matched_symbols(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return [symbol for symbol in REQUIRED_OLD_SYMBOLS if symbol in text]


def should_scan_file(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.suffix.lower() in {".pyc", ".pyo"}:
        return False
    if path.suffix.lower() not in TEXT_LIKE_SUFFIXES:
        return False
    return not any(part in GENERATED_DIR_NAMES for part in path.parts)


def directory_symbol_summary(path: Path) -> list[str]:
    found: set[str] = set()
    for candidate in path.rglob("*"):
        if should_scan_file(candidate):
            found.update(matched_symbols(candidate))
    return sorted(found)


def _counts(items: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total_items": len(items),
        "rewrite_in_phase_15": sum(1 for entry in items if entry["required_action"] == "rewrite_in_phase_15"),
        "delete_in_phase_16": sum(1 for entry in items if entry["required_action"] == "delete_in_phase_16"),
        "keep_as_non_kernel": sum(1 for entry in items if entry["required_action"] == "keep_as_non_kernel"),
        "state_archive_or_ignore": sum(1 for entry in items if entry["required_action"] in {"archive_or_ignore_state", "no_action_generated_artifact"}),
    }
