from __future__ import annotations

from pathlib import Path

from conftest import PIPELINE_ROOT
from edit_suite.contract_runtime import invoke_owner_contract
from edit_suite.registry.types import ModuleReadinessEntry
from edit_suite.surfaces.load_bundle import load_bundle
from edit_suite.surfaces.sections import build_sections


def _entry(module_root: Path) -> ModuleReadinessEntry:
    return ModuleReadinessEntry(
        slot_name=module_root.name,
        display_name="MCP Server",
        module_root=str(module_root.resolve()),
        module_key="mcp_server",
        readiness="ready",
        blockers=(),
        manifest_path=str((module_root / "module-manifest.json").resolve()),
        manifest_present=True,
        edit_contract_path=str((module_root / "mcp_server" / "edit_contract").resolve()),
        runtime_available=True,
    )


def test_mcp_server_bundle_exposes_support_monitor_surface(tmp_path: Path) -> None:
    module_root = PIPELINE_ROOT / "07 - MCP Server"

    payload = invoke_owner_contract(
        module_root=module_root,
        contract_path=str((module_root / "mcp_server" / "edit_contract").resolve()),
        state_root=tmp_path / "state",
        payload={"action": "describe_surfaces"},
    )

    assert payload["status"] == "ok"
    assert [surface["surface_id"] for surface in payload["surfaces"]] == ["mcp_server.support_monitor"]
    assert payload["surfaces"][0]["validation"]["fail_closed"] is True

    bundle = load_bundle(_entry(module_root), state_root=tmp_path / "state")
    sections = {section.name: section for section in build_sections(_entry(module_root), bundle, {})}

    assert [surface.surface_id for surface in sections["Operations"].surfaces] == ["mcp_server.support_monitor"]
    assert sections["Operations"].surfaces[0].editor_kind == "support_monitor"
