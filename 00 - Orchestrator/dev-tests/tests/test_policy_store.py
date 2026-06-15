from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchestrator import policy_store
from orchestrator.policy_store import repository

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = PROJECT_ROOT / "dev-tests" / "fixtures" / "policy_defaults"
LOADERS = (
    (policy_store.ROUTE_INTAKE_SURFACE_ID, policy_store.load_route_intake_policy),
    (policy_store.EXECUTION_SURFACE_ID, policy_store.load_execution_policy),
    (policy_store.HEALTH_DEPENDENCY_SURFACE_ID, policy_store.load_health_dependency_policy),
    (policy_store.ARTIFACT_PUBLICATION_SURFACE_ID, policy_store.load_artifact_publication_policy),
)


def _fixture_payload(surface_id: str) -> dict:
    file_name = Path(policy_store.SURFACE_FILES[surface_id]).name
    return json.loads((FIXTURE_ROOT / file_name).read_text(encoding="utf-8"))


def test_checked_in_config_matches_frozen_fixtures() -> None:
    for surface_id in policy_store.SURFACE_IDS:
        checked_in = json.loads((PROJECT_ROOT / policy_store.SURFACE_FILES[surface_id]).read_text(encoding="utf-8"))
        assert checked_in == _fixture_payload(surface_id)


@pytest.mark.parametrize(("surface_id", "loader"), LOADERS)
def test_loaders_return_canonical_payloads(surface_id: str, loader) -> None:
    assert loader() == _fixture_payload(surface_id)


def test_policy_store_reloads_changed_files_on_next_load(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    surface_id = policy_store.EXECUTION_SURFACE_ID
    target = tmp_path / "execution_policy.json"
    target.write_text(json.dumps(_fixture_payload(surface_id), indent=2), encoding="utf-8")
    monkeypatch.setattr(repository, "surface_path", lambda _surface_id: target)
    repository.invalidate_cache(surface_id)

    first = repository.load_surface(surface_id)
    updated = dict(first)
    updated["projection_catalog_timeout_seconds"] = 91
    target.write_text(json.dumps(updated, indent=2), encoding="utf-8")

    reread = repository.load_surface(surface_id)

    assert first["projection_catalog_timeout_seconds"] == 60
    assert reread["projection_catalog_timeout_seconds"] == 91


def test_policy_validation_fails_closed_for_missing_and_extra_fields() -> None:
    route_payload = _fixture_payload(policy_store.ROUTE_INTAKE_SURFACE_ID)
    missing = dict(route_payload)
    missing.pop("pdf_routing")
    extra = dict(route_payload)
    extra["unexpected"] = True

    with pytest.raises(ValueError, match="unexpected or incorrectly sorted fields"):
        policy_store.validate_surface_value(policy_store.ROUTE_INTAKE_SURFACE_ID, missing)

    with pytest.raises(ValueError, match="unexpected or incorrectly sorted fields"):
        policy_store.validate_surface_value(policy_store.ROUTE_INTAKE_SURFACE_ID, extra)


def test_policy_validation_rejects_unknown_dependency_modules() -> None:
    payload = _fixture_payload(policy_store.HEALTH_DEPENDENCY_SURFACE_ID)
    payload["scope_profiles"]["pipeline_run"]["unknown_module"] = {".pdf": ["broken"]}

    with pytest.raises(ValueError, match="unknown_module"):
        policy_store.validate_surface_value(policy_store.HEALTH_DEPENDENCY_SURFACE_ID, payload)


def test_surface_paths_refuse_writes_outside_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(repository.SURFACE_FILES, policy_store.ROUTE_INTAKE_SURFACE_ID, r"..\state\ui_state.json")

    with pytest.raises(ValueError, match=r"config/\*\.json"):
        repository.surface_path(policy_store.ROUTE_INTAKE_SURFACE_ID)
