from __future__ import annotations

import json
from pathlib import Path

import ingestion_layer_file.orchestrator_contract as file_contract
import ingestion_layer_vision.orchestrator_contract as contract
from ingestion_layer_file.orchestrator_contract.types import HEALTHCHECK_DEPENDENCIES as FILE_HEALTHCHECK_DEPENDENCIES
from ingestion_layer_vision.orchestrator_contract import healthcheck_routing
from orchestrator_contract_support import DummyPluginManager


def test_orchestrator_policy_dependencies_are_routed_by_merged_optimizer_healthcheck() -> None:
    dependencies = [*_orchestrator_policy_optimizer_dependencies(), "optimizer_ocr"]
    file_dependency_names = set(FILE_HEALTHCHECK_DEPENDENCIES)
    vision_dependency_names = set(healthcheck_routing.VISION_DEPENDENCIES)

    unknown = [
        dependency
        for dependency in dependencies
        if dependency not in file_dependency_names and dependency not in vision_dependency_names
    ]
    assert unknown == []

    split = healthcheck_routing.split_payloads({"required_dependencies": dependencies})
    assert split is not None
    file_payload, vision_payload = split

    assert file_payload is not None
    assert vision_payload is not None
    assert file_payload["optimizer_profile"] == "file"
    assert vision_payload["optimizer_profile"] == "vision"
    assert file_payload["required_dependencies"] == [
        dependency for dependency in dependencies if dependency in file_dependency_names
    ]
    assert vision_payload["required_dependencies"] == [
        dependency for dependency in dependencies if dependency in vision_dependency_names
    ]
    assert sorted([*file_payload["required_dependencies"], *vision_payload["required_dependencies"]]) == sorted(dependencies)


def test_healthcheck_reports_required_pdf_runtime(monkeypatch) -> None:
    manager = DummyPluginManager({"pdf-pdfplumber": (False, "No module named '_cffi_backend'")})
    monkeypatch.setattr(contract, "load_config", lambda _path: object())
    monkeypatch.setattr(contract, "PluginManager", lambda *_args, **_kwargs: manager)
    monkeypatch.setattr(
        "ingestion_layer_vision.orchestrator_contract.healthcheck_workflow.check_readiness",
        lambda: (True, "optimizer_ocr bereit"),
    )

    response = contract._healthcheck({})

    assert response["status"] == "error"
    assert response["healthy"] is False
    assert response["message"] == "Core-Extraktoren des Optimizers sind nicht verfuegbar."
    assert response["dependencies"] == [
        {"name": "pdf-pdfplumber", "kind": "runtime", "required": True, "healthy": False, "detail": "No module named '_cffi_backend'"},
        {"name": "optimizer_ocr", "kind": "llm", "required": False, "healthy": True, "detail": "optimizer_ocr bereit"},
    ]
    assert manager.calls == ["pdf-pdfplumber", "kill_all"]


def test_healthcheck_keeps_optimizer_ocr_optional_by_default(monkeypatch) -> None:
    manager = DummyPluginManager({"pdf-pdfplumber": (True, "OK (v2.0.0)")})
    monkeypatch.setattr(contract, "load_config", lambda _path: object())
    monkeypatch.setattr(contract, "PluginManager", lambda *_args, **_kwargs: manager)
    monkeypatch.setattr(
        "ingestion_layer_vision.orchestrator_contract.healthcheck_workflow.check_readiness",
        lambda: (False, "optimizer_ocr API-Key fehlt."),
    )

    response = contract._healthcheck({})

    assert response["status"] == "ok"
    assert response["healthy"] is True
    assert response["dependencies"] == [
        {"name": "pdf-pdfplumber", "kind": "runtime", "required": True, "healthy": True, "detail": "OK (v2.0.0)"},
        {"name": "optimizer_ocr", "kind": "llm", "required": False, "healthy": False, "detail": "optimizer_ocr API-Key fehlt."},
    ]
    assert manager.calls == ["pdf-pdfplumber", "kill_all"]


def test_healthcheck_fails_when_pipeline_requires_optimizer_ocr(monkeypatch) -> None:
    manager = DummyPluginManager({"pdf-pdfplumber": (True, "OK (v2.0.0)")})
    monkeypatch.setattr(contract, "load_config", lambda _path: object())
    monkeypatch.setattr(contract, "PluginManager", lambda *_args, **_kwargs: manager)
    monkeypatch.setattr(
        "ingestion_layer_vision.orchestrator_contract.healthcheck_workflow.check_readiness",
        lambda: (False, "optimizer_ocr API-Key fehlt."),
    )

    response = contract._healthcheck({"required_dependencies": ["pdf-pdfplumber", "optimizer_ocr"]})

    assert response["status"] == "error"
    assert response["healthy"] is False
    assert response["dependencies"][1] == {
        "name": "optimizer_ocr",
        "kind": "llm",
        "required": True,
        "healthy": False,
        "detail": "optimizer_ocr API-Key fehlt.",
    }


def test_healthcheck_passes_when_pipeline_requires_optimizer_ocr_and_config_is_ready(monkeypatch) -> None:
    manager = DummyPluginManager({"pdf-pdfplumber": (True, "OK (v2.0.0)")})
    monkeypatch.setattr(contract, "load_config", lambda _path: object())
    monkeypatch.setattr(contract, "PluginManager", lambda *_args, **_kwargs: manager)
    monkeypatch.setattr(
        "ingestion_layer_vision.orchestrator_contract.healthcheck_workflow.check_readiness",
        lambda: (True, "optimizer_ocr bereit"),
    )

    response = contract._healthcheck({"required_dependencies": ["pdf-pdfplumber", "optimizer_ocr"]})

    assert response["status"] == "ok"
    assert response["healthy"] is True
    assert response["dependencies"][-1] == {
        "name": "optimizer_ocr",
        "kind": "llm",
        "required": True,
        "healthy": True,
        "detail": "optimizer_ocr bereit",
    }


def test_merged_healthcheck_splits_file_and_vision_required_dependencies(monkeypatch) -> None:
    manager = DummyPluginManager({"pdf-pdfplumber": (True, "OK (v2.0.0)")})
    renderer_checks = [
        {"name": "renderer-html", "kind": "runtime", "required": True, "healthy": True, "detail": "OK"},
    ]
    monkeypatch.setattr(contract, "load_config", lambda _path: object())
    monkeypatch.setattr(contract, "PluginManager", lambda *_args, **_kwargs: manager)
    monkeypatch.setattr(
        "ingestion_layer_vision.orchestrator_contract.healthcheck_workflow.check_readiness",
        lambda: (True, "optimizer_ocr bereit"),
    )
    monkeypatch.setattr(file_contract, "load_config", lambda _path: object())
    monkeypatch.setattr(file_contract, "PluginManager", lambda *_args, **_kwargs: manager)
    monkeypatch.setattr(file_contract, "renderer_dependency_selftests", lambda **_kwargs: renderer_checks)

    response = contract._healthcheck({"scope": "pipeline_run", "required_dependencies": ["renderer-html", "optimizer_ocr"]})

    assert response["status"] == "ok"
    assert response["healthy"] is True
    assert renderer_checks[0] in response["dependencies"]
    assert response["dependencies"][-1]["name"] == "optimizer_ocr"
    assert response["dependencies"][-1]["healthy"] is True


def _orchestrator_policy_optimizer_dependencies() -> list[str]:
    policy_path = (
        Path(__file__).resolve().parents[3]
        / "00 - Orchestrator"
        / "config"
        / "health_dependency_policy.json"
    )
    payload = json.loads(policy_path.read_text(encoding="utf-8"))
    suffix_policy = payload["scope_profiles"]["pipeline_run"]["optimizer"]
    dependencies: list[str] = []
    for suffix_dependencies in suffix_policy.values():
        for dependency in suffix_dependencies:
            if dependency not in dependencies:
                dependencies.append(dependency)
    assert dependencies
    return dependencies
