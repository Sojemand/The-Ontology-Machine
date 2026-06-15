from __future__ import annotations

import json
from pathlib import Path

from semantic_control_kernel.adapters.corpus import CorpusAdapter


def test_corpus_adapter_reset_translates_kernel_payload_to_owner_contract(monkeypatch, tmp_path) -> None:
    adapter = CorpusAdapter(state_root=tmp_path / "state", pipeline_root=tmp_path)
    db_path = tmp_path / "Artifact Tree" / "Corpus" / "corpus.db"
    db_path.parent.mkdir(parents=True)
    db_path.write_text("", encoding="utf-8")
    captured = {}

    def fake_invoke(**kwargs):
        captured.update(kwargs)
        return adapter.ok_result(
            kernel_function="reset_database",
            capability_status="kernel_composition_over_existing_primitives",
            output_refs={
                "database_path": str(db_path),
                "semantic_release_preserved": True,
                "empty_state_proven": True,
            },
            target_identity_proof={"database_path": str(db_path)},
        )

    monkeypatch.setattr(adapter, "invoke", fake_invoke)

    result = adapter.reset_database(
        {
            "database_path": str(db_path),
            "target_identity": {"database_path_hash": adapter.owner_path_hash(db_path)},
            "confirmation": {"confirmation_receipt_id": "cfr_reset_adapter", "user_decision": "confirmed"},
        }
    )

    owner_request = captured["request_payload"]
    confirmation_artifact = Path(owner_request["confirmation_artifact_path"])
    confirmation_payload = json.loads(confirmation_artifact.read_text(encoding="utf-8"))
    assert result.status == "ok"
    assert owner_request["action"] == "reset_active_corpus_db"
    assert owner_request["corpus_db_path"] == str(db_path)
    assert confirmation_payload["artifact_version"] == "reset_active_corpus_db_confirmation_v1"
    assert confirmation_payload["requested_action"] == "reset_active_corpus_db"
    assert confirmation_payload["confirmed"] is True
    assert confirmation_payload["corpus_db_path"] == str(db_path.resolve(strict=False))


def test_corpus_adapter_read_active_release_sends_owner_action(monkeypatch, tmp_path) -> None:
    adapter = CorpusAdapter(state_root=tmp_path / "state", pipeline_root=tmp_path)
    db_path = tmp_path / "Artifact Tree" / "Corpus" / "corpus.db"
    captured = {}

    def fake_invoke(**kwargs):
        captured.update(kwargs)
        return adapter.ok_result(
            kernel_function="read_active_semantic_release",
            capability_status="implemented_in_pipeline",
            output_refs={"release_id": "semantic_release.custom"},
        )

    monkeypatch.setattr(adapter, "invoke", fake_invoke)

    result = adapter.read_active_semantic_release({"corpus_db_path": str(db_path)})

    assert result.status == "ok"
    assert captured["request_payload"]["action"] == "read_active_semantic_release"
    assert captured["request_payload"]["corpus_db_path"] == str(db_path)
