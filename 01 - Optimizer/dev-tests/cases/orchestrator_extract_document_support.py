from __future__ import annotations

import json

import ingestion_layer_vision.orchestrator_contract as contract

from orchestrator_contract_support import runtime_policy_payload


def _install_extract_common(monkeypatch, manager, processor_cls) -> None:
    monkeypatch.setattr(contract, "load_config", lambda _path: object())
    monkeypatch.setattr(contract, "PluginManager", lambda *_args, **_kwargs: manager)
    monkeypatch.setattr(contract, "Processor", processor_cls)


def _runtime_policy_path(tmp_path):
    runtime_policy_path = tmp_path / "runtime_semantic_assets.json"
    runtime_policy_path.write_text(json.dumps(runtime_policy_payload()), encoding="utf-8")
    return runtime_policy_path
