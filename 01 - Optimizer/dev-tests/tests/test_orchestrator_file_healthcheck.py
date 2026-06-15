from __future__ import annotations

import ingestion_layer_file.orchestrator_contract as file_contract
from orchestrator_contract_support import DummyPluginManager


def test_file_healthcheck_keeps_outlook_store_optional_by_default(monkeypatch) -> None:
    manager = DummyPluginManager(
        {
            "pdf-pymupdf": (True, "OK"),
            "docx-python": (True, "OK"),
            "odt-odfpy": (True, "OK"),
            "rtf-reader": (True, "OK"),
            "mail-rfc822": (True, "OK"),
            "mail-outlook-msg": (True, "OK"),
            "mail-outlook-store": (False, "pypff nicht verfuegbar"),
        }
    )
    monkeypatch.setattr(file_contract, "load_config", lambda _path: object())
    monkeypatch.setattr(file_contract, "PluginManager", lambda *_args, **_kwargs: manager)
    monkeypatch.setattr(
        file_contract,
        "renderer_dependency_selftests",
        lambda **_kwargs: [
            {"name": "renderer-pdf", "kind": "runtime", "required": True, "healthy": True, "detail": "OK"},
            {"name": "renderer-office", "kind": "runtime", "required": True, "healthy": True, "detail": "OK"},
            {"name": "renderer-html", "kind": "runtime", "required": True, "healthy": True, "detail": "OK"},
        ],
    )

    response = file_contract._healthcheck({})

    assert response["status"] == "ok"
    assert response["healthy"] is True
    outlook = next(item for item in response["dependencies"] if item["name"] == "mail-outlook-store")
    assert outlook == {
        "name": "mail-outlook-store",
        "kind": "runtime",
        "required": False,
        "healthy": False,
        "detail": "pypff nicht verfuegbar",
    }


def test_file_healthcheck_fails_when_outlook_store_is_required(monkeypatch) -> None:
    manager = DummyPluginManager({"mail-outlook-store": (False, "pypff nicht verfuegbar")})
    monkeypatch.setattr(file_contract, "load_config", lambda _path: object())
    monkeypatch.setattr(file_contract, "PluginManager", lambda *_args, **_kwargs: manager)
    monkeypatch.setattr(file_contract, "renderer_dependency_selftests", lambda **_kwargs: [])

    response = file_contract._healthcheck(
        {"scope": "pipeline_run", "required_dependencies": ["mail-outlook-store"]}
    )

    assert response["status"] == "error"
    assert response["healthy"] is False
    assert response["dependencies"][-1] == {
        "name": "mail-outlook-store",
        "kind": "runtime",
        "required": True,
        "healthy": False,
        "detail": "pypff nicht verfuegbar",
    }
    assert manager.calls == ["mail-outlook-store", "kill_all"]
