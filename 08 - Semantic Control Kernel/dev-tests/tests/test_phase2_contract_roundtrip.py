from __future__ import annotations

import json
from pathlib import Path

from semantic_control_kernel.types.registry import CONTRACT_REGISTRY
from semantic_control_kernel.validation.contract_validation import (
    parse_contract,
    serialize_contract,
    validate_contract_roundtrip,
)


MODULE_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = MODULE_ROOT / "dev-tests" / "fixtures" / "contracts"


def _fixture_name(schema_version: str) -> str:
    return schema_version.replace(".", "__") + ".valid.json"


def test_every_non_reference_contract_has_valid_fixture() -> None:
    expected = {
        _fixture_name(schema_version)
        for schema_version, entry in CONTRACT_REGISTRY.items()
        if entry.validation_depth != "reference_only"
    }
    actual = {path.name for path in FIXTURE_ROOT.glob("*.valid.json")}

    assert actual == expected


def test_reference_only_entries_do_not_have_object_fixtures() -> None:
    for schema_version, entry in CONTRACT_REGISTRY.items():
        if entry.validation_depth == "reference_only":
            assert not (FIXTURE_ROOT / _fixture_name(schema_version)).exists()


def test_valid_fixtures_round_trip_without_shape_loss() -> None:
    for path in sorted(FIXTURE_ROOT.glob("*.valid.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))

        parsed = parse_contract(payload)
        serialized = serialize_contract(parsed)
        reparsed = parse_contract(serialized)

        assert serialized == payload
        assert serialize_contract(reparsed) == payload
        validate_contract_roundtrip(parsed)
