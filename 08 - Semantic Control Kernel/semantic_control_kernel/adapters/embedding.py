from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.adapters.base import BasePipelineAdapter, LONG_RUNNING_TIMEOUT_SECONDS
from semantic_control_kernel.types.adapter_results import AdapterCallResult


class EmbeddingAdapter(BasePipelineAdapter):
    adapter_name = "EmbeddingAdapter"

    def create_embeddings(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult:
        payload = dict(request_payload or {})
        corpus_db_path = str(payload.get("corpus_db_path") or payload.get("database_path") or "").strip()
        if not corpus_db_path:
            return self.blocked_by_kernel_precondition(
                kernel_function="create_embeddings",
                capability_status="implemented_in_pipeline",
                summary="Embedding creation requires corpus_db_path.",
                missing_fields=("corpus_db_path",),
            )
        database_path = Path(corpus_db_path).resolve(strict=False)
        target_identity = self.target_identity(payload, database_path=database_path)
        return self.invoke(
            kernel_function="create_embeddings",
            owner_module="00 - Orchestrator",
            owner_contract_module="orchestrator.orchestrator_contract",
            owner_action="embeddings",
            request_payload={
                "action": "embeddings",
                "ui_state": {
                    "corpus_output_folder": str(database_path.parent),
                    "selected_corpus_db_path": str(database_path),
                },
            },
            capability_status="implemented_in_pipeline",
            timeout_seconds=LONG_RUNNING_TIMEOUT_SECONDS,
            mutating=True,
            required_target_proof_fields=("database_path|database_path_hash",),
            target_identity=target_identity,
        )
