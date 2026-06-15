from __future__ import annotations

from pathlib import Path

from packaging_contract_support import MODULE_ROOT
from edit_contract_support import _run_contract_with_python


def test_describe_surfaces_bootstraps_without_yaml_site_package(tmp_path: Path) -> None:
    payload = _run_contract_with_python(
        tmp_path,
        {"action": "describe_surfaces"},
        python_args=("-S",),
        extra_env={"PYTHONPATH": str(MODULE_ROOT)},
    )
    assert payload["status"] == "ok"
    assert len(payload["surfaces"]) == 4
    assert payload["module_summary"].startswith("OPTIMIZER HELP")


def test_ocr_prompt_reads_without_yaml_site_package(tmp_path: Path) -> None:
    payload = _run_contract_with_python(
        tmp_path,
        {"action": "read_surface", "surface_id": "optimizer.ocr_prompt"},
        python_args=("-S",),
        extra_env={"PYTHONPATH": str(MODULE_ROOT)},
    )
    assert payload["status"] == "ok"
    assert "{page_count}" in payload["value"]["ocr_prompt_md"]


def test_output_contract_preview_reads_without_yaml_site_package(tmp_path: Path) -> None:
    payload = _run_contract_with_python(
        tmp_path,
        {"action": "read_surface", "surface_id": "optimizer.output_contract_preview"},
        python_args=("-S",),
        extra_env={"PYTHONPATH": str(MODULE_ROOT)},
    )
    assert payload["status"] == "ok"
    assert payload["value"]["llm_ocr_runtime"]["dependency"] == "optimizer_ocr"


def test_debug_capabilities_reads_without_yaml_site_package(tmp_path: Path) -> None:
    payload = _run_contract_with_python(
        tmp_path,
        {"action": "read_surface", "surface_id": "optimizer.debug_capabilities"},
        python_args=("-S",),
        extra_env={"PYTHONPATH": str(MODULE_ROOT)},
    )
    assert payload["status"] == "ok"
    assert payload["value"]["operation_links"]


def test_settings_surface_stays_fail_closed_without_yaml_site_package(tmp_path: Path) -> None:
    payload = _run_contract_with_python(
        tmp_path,
        {"action": "read_surface", "surface_id": "optimizer.settings"},
        python_args=("-S",),
        extra_env={"PYTHONPATH": str(MODULE_ROOT)},
    )
    assert payload["status"] == "error"
    assert "yaml" in payload["reason"].lower()
