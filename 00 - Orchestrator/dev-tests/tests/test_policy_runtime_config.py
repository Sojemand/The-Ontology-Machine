from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from orchestrator.integrations.projection_catalog import load_normalizer_projection_catalog
from orchestrator.pipeline import health_profile_policy, intake_workflow, policy, route_policy, storage_repository
from tests.test_integrations_workflow import _runtime_spec


def test_route_policy_uses_loader_backed_suffix_groups(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("orchestrator.pipeline.route_policy.policy_store.image_suffixes", lambda: (".heic",))
    monkeypatch.setattr("orchestrator.pipeline.route_policy.policy_store.file_suffixes", lambda: (".rst",))

    assert route_policy.route_family_for_suffix(".heic") == "Documents"
    assert route_policy.route_family_for_suffix(".rst") == "Documents"
    assert route_policy.route_family_for_suffix(".parquet") == ""


def test_required_live_modules_uses_configured_global_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    records = [SimpleNamespace(optimizer_module_key="optimizer", interpreter_module_key="interpreter")]
    monkeypatch.setattr(
        "orchestrator.pipeline.intake_workflow.policy_store.global_required_modules",
        lambda: ("validator", "corpus_builder"),
    )

    assert intake_workflow.required_live_modules(
        records,
        ("optimizer", "interpreter", "validator", "normalizer", "corpus_builder"),
    ) == ("optimizer", "interpreter", "validator", "corpus_builder")


def test_projection_catalog_uses_policy_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    modules = type("Modules", (), {"_runtime_specs": {"normalizer": _runtime_spec(tmp_path, "normalizer")}})()
    captured: list[int] = []

    def fake_invoke(*_args, **kwargs):
        captured.append(kwargs["timeout"])
        return {
            "status": "OK",
            "projection_catalog": {
                "catalog_version": "sha256:test",
                "master_taxonomy_version": "2026-03-28.v5",
                "projections": [],
            },
        }

    monkeypatch.setattr("orchestrator.integrations.projection_catalog.policy_store.projection_catalog_timeout_seconds", lambda: 91)
    monkeypatch.setattr("orchestrator.integrations.projection_catalog.adapter.invoke_contract", fake_invoke)

    assert load_normalizer_projection_catalog(modules)["catalog_version"] == "sha256:test"
    assert captured == [91]


def test_health_profile_policy_uses_fallback_scope_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    record = SimpleNamespace(
        file_name="notes.md",
        source_path="notes.md",
        original_source_path="notes.md",
        optimizer_module_key="optimizer",
    )
    monkeypatch.setattr("orchestrator.pipeline.health_profile_policy.policy_store.dependency_scope_profile", lambda _scope: {})
    monkeypatch.setattr(
        "orchestrator.pipeline.health_profile_policy.policy_store.fallback_dependency_profile",
        lambda: {"optimizer": {".md": ["renderer-html"]}},
    )

    assert health_profile_policy.build_required_dependencies_by_module([record], scope="manual_check") == {
        "optimizer": ("renderer-html",),
    }


def test_publication_roots_and_request_names_use_policy_accessors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("orchestrator.pipeline.storage_repository.policy_store.publication_name", lambda key: {"logs": "trace"}[key])
    monkeypatch.setattr("orchestrator.pipeline.policy.policy_store.request_file_name", lambda _key: "custom.request.json")
    record = SimpleNamespace(relative_path="doc.pdf", file_name="doc.pdf", source_path="doc.pdf", original_source_path="doc.pdf")

    assert storage_repository.publication_root(tmp_path, "logs") == tmp_path / "trace"
    assert policy.interpreter_request_output_path(object(), record) == Path("doc.pdf") / "custom.request.json"

