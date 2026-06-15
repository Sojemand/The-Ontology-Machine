from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import PIPELINE_ROOT
from edit_suite.contract_runtime import invoke_owner_contract
from edit_suite.surfaces.section_assignment import section_name_for_descriptor

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "as_built"
SECTION_ORDER = ("Settings", "Prompts/Assets", "Operations", "Preview/Drift")
CASES = (
    {
        "slot_name": "01 - Optimizer",
        "env_name": "OPTIMIZER_HOME",
        "surface_fixture": "optimizer_describe_surfaces.json",
        "summary_fixture": "optimizer_summary.txt",
        "expected_sections": {
            "Settings": ["optimizer.settings"],
            "Prompts/Assets": ["optimizer.ocr_prompt"],
            "Operations": ["optimizer.debug_capabilities"],
            "Preview/Drift": ["optimizer.output_contract_preview"],
        },
    },
)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["slot_name"])
def test_owner_contract_describe_surfaces_matches_as_built_fixture(case, tmp_path: Path, monkeypatch) -> None:
    payload = _describe_payload(case, tmp_path=tmp_path, monkeypatch=monkeypatch)

    assert payload["status"] == "ok"
    assert payload["surfaces"] == _load_json(case["surface_fixture"])
    assert payload["module_summary"] == _load_text(case["summary_fixture"])


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["slot_name"])
def test_as_built_surfaces_map_into_stable_suite_sections(case, tmp_path: Path, monkeypatch) -> None:
    payload = _describe_payload(case, tmp_path=tmp_path, monkeypatch=monkeypatch)

    assert _surface_sections(payload["surfaces"]) == case["expected_sections"]


def _describe_payload(case: dict[str, object], *, tmp_path: Path, monkeypatch) -> dict:
    slot_name = str(case["slot_name"])
    module_root = PIPELINE_ROOT / slot_name
    monkeypatch.setenv(str(case["env_name"]), str(tmp_path / (module_root.name.replace(" ", "_") + "_home")))
    return invoke_owner_contract(
        module_root=module_root,
        contract_path=str((module_root / "ingestion_layer_vision" / "edit_contract").resolve()),
        state_root=tmp_path / "state",
        payload={"action": "describe_surfaces"},
    )


def _surface_sections(surfaces: list[dict]) -> dict[str, list[str]]:
    grouped = {name: [] for name in SECTION_ORDER}
    for descriptor in surfaces:
        name = section_name_for_descriptor(descriptor, kind=str(descriptor["kind"]))
        if name in grouped:
            grouped[name].append(str(descriptor["surface_id"]))
    return grouped


def _load_json(name: str) -> object:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _load_text(name: str) -> str:
    return (FIXTURE_ROOT / name).read_text(encoding="utf-8").rstrip("\n")

