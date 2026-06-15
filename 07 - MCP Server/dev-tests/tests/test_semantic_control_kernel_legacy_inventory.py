from __future__ import annotations

import json
from pathlib import Path

from mcp_server.semantic_control_kernel_legacy_inventory import (
    REQUIRED_OLD_SYMBOLS,
    REQUIRED_SCAN_ROOTS,
    build_legacy_inventory,
)


MODULE_ROOT = Path(__file__).resolve().parents[2]


def test_legacy_inventory_scanner_and_committed_artifact_cover_required_roots_and_symbols() -> None:
    generated = build_legacy_inventory(MODULE_ROOT)
    committed = json.loads((MODULE_ROOT / "migration" / "phase14_legacy_cleanup_inventory.json").read_text(encoding="utf-8"))

    assert generated["schema_version"] == "mcp.phase14_legacy_cleanup_inventory.v1"
    assert committed["schema_version"] == generated["schema_version"]
    assert REQUIRED_SCAN_ROOTS
    seen_symbols = {symbol for item in generated["items"] for symbol in item["legacy_symbols"]}
    assert set(REQUIRED_OLD_SYMBOLS) <= seen_symbols
    assert generated["counts"]["total_items"] == len(generated["items"])
    for item in generated["items"]:
        assert item["path"]
        assert item["item_type"]
        assert item["classification"]
        assert item["status_after_phase14"]
        assert item["required_action"]
        assert item["owner_phase"]
        assert item["reason"]
        assert "replacement" in item

