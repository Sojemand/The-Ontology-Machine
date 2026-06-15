from __future__ import annotations

from pathlib import Path

from . import test_phase15_no_old_kernel_imports as phase15_imports
from . import test_phase15_non_kernel_tool_regression as phase15_non_kernel
from . import test_phase15_old_tools_retired as phase15_retired
from . import test_phase15_permissions_semantic_control_kernel as phase15_permissions
from . import test_phase15_product_semantics_no_workflow_family_ids as phase15_product_semantics
from . import test_phase15_registry_unlinked as phase15_registry
from . import test_phase15_runtime_manifest_unlinked as phase15_manifest
from . import test_phase15_state_is_not_runtime_truth as phase15_state


def test_phase15_import_regression() -> None:
    phase15_imports.test_active_mcp_product_files_do_not_import_old_kernel_surface()
    phase15_imports.test_bridge_files_do_not_directly_import_kernel_product_package()
    phase15_imports.test_legacy_test_disposition_covers_all_old_kernel_tests_without_skip_harness()


def test_phase15_retired_surface_regression() -> None:
    phase15_retired.test_old_public_kernel_names_fail_closed_before_legacy_handler_import()


def test_phase15_registry_regression(monkeypatch) -> None:
    phase15_registry.test_registry_and_catalog_are_unlinked_from_old_kernel_names(monkeypatch)


def test_phase15_permissions_regression() -> None:
    phase15_permissions.test_semantic_control_kernel_permissions_are_one_inherited_transport_surface()
    phase15_permissions.test_legacy_recovery_internal_continuation_and_host_only_names_stay_out_of_permanent_permissions()


def test_phase15_runtime_manifest_regression() -> None:
    phase15_manifest.test_runtime_manifest_no_longer_packages_legacy_kernel_payload()


def test_phase15_product_semantics_regression(monkeypatch) -> None:
    phase15_product_semantics.test_product_semantics_outputs_only_canonical_kernel_and_mcp_tool_names(monkeypatch)


def test_phase15_state_policy_regression() -> None:
    phase15_state.test_phase15_state_policy_rejects_legacy_mcp_state_as_fixture()
    phase15_state.test_bridge_and_kernel_state_paths_do_not_use_legacy_mcp_kernel_state()


def test_phase15_non_kernel_tool_regression(tmp_path: Path, monkeypatch) -> None:
    phase15_non_kernel.test_representative_non_kernel_tools_still_dispatch_after_legacy_unlink(monkeypatch, tmp_path)
