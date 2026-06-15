from __future__ import annotations

import re
from pathlib import Path

from semantic_control_kernel.types.base import KernelContract
from semantic_control_kernel.types.registry import CONTRACT_REGISTRY


MODULE_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = MODULE_ROOT.parent
BUILD_SPEC = MODULE_ROOT / "SPEC_Semantic_Control_Kernel_Build.md"
SPEC_11 = PIPELINE_ROOT / "Semantic Kernel SPEC" / "11_kernel_internal_data_contracts.md"

DRIFT_PREFLIGHT = {
    "status": "drift_preflight: build_plan_authority_applied",
    "details": [
        {
            "document": "Semantic Kernel SPEC/11_kernel_internal_data_contracts.md",
            "path": "pipeline_batch_manifest example payload",
            "reason": "example uses stale nested field names and batch_kind value; Phase 2 build-plan nested shape wins",
        }
    ],
}


def _phase2_table_rows() -> list[list[str]]:
    text = BUILD_SPEC.read_text(encoding="utf-8")
    phase_text = text.split("## Phase 2 - Core Types And Internal Data Contracts", 1)[1].split("\n---", 1)[0]
    return _table_rows(phase_text)


def _spec11_table_rows() -> list[list[str]]:
    text = SPEC_11.read_text(encoding="utf-8")
    first_table = text.split("Additional canonical contract entries introduced by later Build phases:", 1)[0]
    return _table_rows(first_table)


def _table_rows(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in text.splitlines():
        if not line.startswith("| `"):
            continue
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) == 7:
            rows.append(parts)
    return rows


def _field_names(cell: str) -> tuple[str, ...]:
    if cell == "none":
        return ()
    return tuple(re.findall(r"`([^`]+)`", cell))


def test_drift_preflight_recorded() -> None:
    assert DRIFT_PREFLIGHT["status"] == "drift_preflight: build_plan_authority_applied"
    assert DRIFT_PREFLIGHT["details"]


def test_registry_contains_exact_phase2_schema_versions() -> None:
    expected = [row[0].strip("`") for row in _phase2_table_rows()]

    assert list(CONTRACT_REGISTRY) == expected
    assert len(CONTRACT_REGISTRY) == 40


def test_spec11_mirrors_phase2_registry_rows() -> None:
    phase_rows = _phase2_table_rows()
    spec_rows = _spec11_table_rows()

    assert spec_rows == phase_rows
    for row in phase_rows:
        schema_version = row[0].strip("`")
        entry = CONTRACT_REGISTRY[schema_version]
        assert entry.required_fields == _field_names(row[4])
        assert entry.optional_fields == _field_names(row[5])
        assert entry.validation_depth == row[6]


def test_registry_has_no_duplicate_schema_versions() -> None:
    schema_versions = list(CONTRACT_REGISTRY)

    assert len(schema_versions) == len(set(schema_versions))


def test_every_registry_entry_has_required_metadata_and_named_type() -> None:
    for schema_version, entry in CONTRACT_REGISTRY.items():
        assert entry.schema_version == schema_version
        assert entry.producer
        assert entry.consumers
        assert entry.persistence
        assert entry.source_spec
        assert isinstance(entry.required_fields, tuple)
        assert isinstance(entry.optional_fields, tuple)
        assert entry.extension_policy in {"closed_object", "reference_only"}
        assert entry.validation_depth in {"closed_top_level", "closed_deep", "reference_only"}
        assert issubclass(entry.python_type, KernelContract)
        assert entry.python_type.__name__
        assert entry.python_type.SCHEMA_VERSION == schema_version


def test_required_field_cells_are_explicit_or_none() -> None:
    forbidden = {"same as", "source route view identifier"}

    for row in _phase2_table_rows():
        cell = row[4]
        assert cell == "none" or _field_names(cell)
        assert all(fragment not in cell.lower() for fragment in forbidden)
