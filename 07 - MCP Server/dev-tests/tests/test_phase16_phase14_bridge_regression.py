from __future__ import annotations

from pathlib import Path

from . import test_semantic_control_kernel_event_scoped_recovery as phase14_recovery
from . import test_semantic_control_kernel_host_only_client_bridge as phase14_host_bridge
from . import test_semantic_control_kernel_mcp_catalog as phase14_catalog
from . import test_semantic_control_kernel_mcp_dispatch as phase14_dispatch
from . import test_semantic_control_kernel_mcp_visibility as phase14_visibility


def test_phase14_catalog_regression(monkeypatch) -> None:
    phase14_catalog.test_catalog_exposes_permanent_semantic_control_kernel_names_only(monkeypatch)


def test_phase14_dispatch_regression(monkeypatch) -> None:
    phase14_dispatch.test_handlers_forward_canonical_tools_with_expected_visibility_and_empty_model_arguments(monkeypatch)


def test_phase14_visibility_regression() -> None:
    phase14_visibility.test_visibility_classifies_permanent_event_scoped_internal_continuation_host_only_legacy_and_unknown_names()
    phase14_visibility.test_direct_legacy_internal_and_continuation_calls_fail_closed()


def test_phase14_event_scoped_recovery_regression(tmp_path: Path, monkeypatch) -> None:
    phase14_recovery.test_event_scoped_tool_definitions_follow_active_kernel_recovery_scope(
        tmp_path / "active",
        monkeypatch,
    )
    phase14_recovery.test_stale_or_resolved_event_scoped_requests_fail_closed(tmp_path / "stale")
    phase14_recovery.test_expired_event_scoped_availability_returns_typed_expired_response(tmp_path / "expired")


def test_phase14_host_only_bridge_regression(tmp_path: Path) -> None:
    phase14_host_bridge.test_host_only_bridge_reads_events_and_persists_submit_and_cancel(tmp_path / "events")
    phase14_host_bridge.test_host_bridge_rejects_stale_identities(tmp_path / "stale")
    phase14_host_bridge.test_host_bridge_tools_stay_out_of_normal_agent_surface()
