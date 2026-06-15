from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.services.agent_tool_invocation_service import AgentToolInvocationService
from semantic_control_kernel.types.agent_tools import REJECTED_LEGACY_AGENT_SURFACE_NAMES


MODULE_ROOT = Path(__file__).resolve().parents[2]


def test_every_rejected_legacy_name_fails_closed() -> None:
    service = AgentToolInvocationService()

    for name in REJECTED_LEGACY_AGENT_SURFACE_NAMES:
        result = service.invoke(name, invocation_context={}, model_payload={}).to_dict()
        assert result["status"] == "rejected"
        assert result["error"]["code"] == "legacy_agent_surface_rejected"


def test_public_agent_files_do_not_export_legacy_surface_names() -> None:
    scanned_files = (
        MODULE_ROOT / "semantic_control_kernel" / "surface" / "agent_tools.py",
        MODULE_ROOT / "semantic_control_kernel" / "orchestrator_contract.py",
        MODULE_ROOT / "README.md",
    )

    for path in scanned_files:
        text = path.read_text(encoding="utf-8")
        for name in REJECTED_LEGACY_AGENT_SURFACE_NAMES:
            assert name not in text, f"{name} leaked into {path.relative_to(MODULE_ROOT)}"
