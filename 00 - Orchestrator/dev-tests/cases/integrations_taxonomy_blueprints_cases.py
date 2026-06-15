from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator import policy_store
from orchestrator.integrations.taxonomy_blueprints import (
    export_default_blueprint_release,
    list_default_blueprints,
)
from orchestrator.integrations.types import ModuleContractError

from tests.test_integrations_workflow import _runtime_spec


def test_list_default_blueprints_prefers_direct_provider() -> None:
    class Modules:
        def list_default_blueprints(self) -> dict[str, object]:
            return {
                "blueprints": [
                    {"blueprint_ref": "default", "label": "Default Canonical"},
                ]
            }

    detail = list_default_blueprints(Modules())

    assert [item["blueprint_ref"] for item in detail] == ["default"]


def test_list_default_blueprints_invokes_contract_and_unwraps_payload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    modules = type(
        "Modules",
        (),
        {
            "_runtime_specs": {
                "normalizer": _runtime_spec(tmp_path, "normalizer"),
            }
        },
    )()
    captured: list[tuple[str, dict[str, object], int]] = []

    def fake_invoke(spec, payload, *, timeout, env_overlay=None):  # noqa: ANN001
        del env_overlay
        captured.append((spec.key, payload, timeout))
        return {
            "status": "OK",
            "blueprints": [
                {"blueprint_ref": "default", "label": "Default Canonical"},
            ],
        }

    monkeypatch.setattr("orchestrator.integrations.taxonomy_blueprints.adapter.invoke_contract", fake_invoke)

    detail = list_default_blueprints(modules)

    assert captured == [
        (
            "normalizer",
            {
                "action": "list_default_blueprints",
            },
            policy_store.projection_catalog_timeout_seconds(),
        )
    ]
    assert detail[0]["blueprint_ref"] == "default"


def test_export_default_blueprint_release_invokes_contract_and_validates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    modules = type(
        "Modules",
        (),
        {
            "_runtime_specs": {
                "normalizer": _runtime_spec(tmp_path, "normalizer"),
            }
        },
    )()
    captured: list[tuple[str, dict[str, object], int]] = []
    output_path = tmp_path / "release" / "default.release.json"

    def fake_invoke(spec, payload, *, timeout, env_overlay=None):  # noqa: ANN001
        del env_overlay
        captured.append((spec.key, payload, timeout))
        return {
            "status": "OK",
            "blueprint_ref": "default",
            "output_path": str(output_path),
            "release_id": "semantic_release.default",
            "release_version": "2026-03-28.v6",
        }

    monkeypatch.setattr("orchestrator.integrations.taxonomy_blueprints.adapter.invoke_contract", fake_invoke)

    detail = export_default_blueprint_release(
        modules,
        blueprint_ref="default",
        target_locale="en",
        output_path=output_path,
    )

    assert captured == [
        (
            "normalizer",
            {
                "action": "export_default_blueprint_release",
                "blueprint_ref": "default",
                "target_locale": "en",
                "output_path": str(output_path),
            },
            policy_store.projection_catalog_timeout_seconds(),
        )
    ]
    assert detail["output_path"] == str(output_path)
    assert detail["release_id"] == "semantic_release.default"


def test_export_default_blueprint_release_rejects_error_payload(tmp_path: Path) -> None:
    class Modules:
        def export_default_blueprint_release(self, blueprint_ref: str, output_path: Path, *, target_locale: str | None = None) -> dict[str, object]:
            del blueprint_ref, output_path, target_locale
            return {"status": "ERROR", "error": "blocked"}

    with pytest.raises(ModuleContractError, match="blocked"):
        export_default_blueprint_release(
            Modules(),
            blueprint_ref="default",
            target_locale="de",
            output_path=tmp_path / "release.json",
        )
