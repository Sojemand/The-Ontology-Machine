from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.adapters.corpus import CorpusAdapter
from semantic_control_kernel.adapters.registry import CANONICAL_FUNCTION_ADAPTER_MAP
from semantic_control_kernel.types.adapter_results import AdapterCallResult
from semantic_control_kernel.workflows.ontology import basic_relation_mining


class CapturingCorpusAdapter(CorpusAdapter):
    def __init__(self, *, state_root: str | Path, pipeline_root: str | Path | None = None) -> None:
        super().__init__(state_root=state_root, pipeline_root=pipeline_root)
        self.captured: dict[str, object] = {}

    def invoke(self, **kwargs) -> AdapterCallResult:  # type: ignore[override]
        self.captured = dict(kwargs)
        request_payload = dict(kwargs.get("request_payload") or {})
        database_path = str(request_payload.get("corpus_db_path") or "")
        return self.ok_result(
            kernel_function=str(kwargs["kernel_function"]),
            capability_status=str(kwargs["capability_status"]),
            output_refs={
                "database_path": database_path,
                "corpus_db_path": database_path,
                "source_documents": 1,
                "source_document_pages": 2,
                "relations_inserted": 4,
            },
            target_identity_proof={"database_path": database_path},
            receipt_fields={"owner_action": kwargs["owner_action"]},
        )


def test_registry_maps_ontology_kernel_functions() -> None:
    assert CANONICAL_FUNCTION_ADAPTER_MAP["basic_relation_mining"].categories == ("CorpusAdapter",)
    assert CANONICAL_FUNCTION_ADAPTER_MAP["basic_relation_mining"].methods == ("basic_relation_mining",)
    assert CANONICAL_FUNCTION_ADAPTER_MAP["ontology_patch_validation"].categories == (
        "kernel_internal_no_pipeline_adapter",
    )


def test_corpus_adapter_basic_relation_mining_builds_owner_request(tmp_path: Path) -> None:
    adapter = CapturingCorpusAdapter(state_root=tmp_path / "state")

    result = adapter.basic_relation_mining({"corpus_db_path": "C:/tmp/corpus.db", "dry_run": True})

    assert result.status == "ok"
    assert adapter.captured["kernel_function"] == "basic_relation_mining"
    assert adapter.captured["owner_action"] == "basic_relation_mining"
    assert adapter.captured["mutating"] is False
    assert adapter.captured["request_payload"] == {
        "action": "basic_relation_mining",
        "corpus_db_path": "C:/tmp/corpus.db",
        "dry_run": True,
    }


def test_kernel_basic_relation_mining_wrapper_returns_output(tmp_path: Path) -> None:
    adapter = CapturingCorpusAdapter(state_root=tmp_path / "state")

    output, adapter_result, blocker = basic_relation_mining(
        adapter,
        target_database_path="C:/tmp/corpus.db",
    )

    assert blocker is None
    assert adapter_result is not None
    assert output is not None
    assert output["source_documents"] == 1
    assert output["relations_inserted"] == 4
