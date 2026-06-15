from __future__ import annotations

from pathlib import Path
from typing import Any

from semantic_control_kernel.policy.rebuild_policy import DEFAULT_EMBEDDING_POLICY, embedding_result_from_policy
from semantic_control_kernel.types.rebuild import RebuildWorkflowBlocker
from semantic_control_kernel.workflows.rebuild.semantic_release_load import _adapter_output, _blocker_from_result


def create_embeddings(
    embedding_adapter: object,
    *,
    target_database_path: str | Path,
    embedding_policy: str = DEFAULT_EMBEDDING_POLICY,
    provider_configured: bool = False,
) -> tuple[str, object | None, RebuildWorkflowBlocker | None]:
    initial_result, code = embedding_result_from_policy(
        policy=embedding_policy,
        provider_configured=provider_configured,
    )
    if code == "embedding_provider_unavailable":
        return initial_result, None, RebuildWorkflowBlocker(
            blocker_code=code,
            step_id="creating_embeddings",
            function_or_route="create_embeddings",
            recovery_state_class="support_only_unrecoverable",
            user_visible_summary="Embedding provider configuration is required for this rebuild.",
        )
    if initial_result == "skipped_unconfigured":
        return "skipped_unconfigured", None, None
    result = embedding_adapter.create_embeddings({"corpus_db_path": str(Path(target_database_path).resolve(strict=False))})
    blocker = _blocker_from_result("creating_embeddings", result, "create_embeddings")
    if blocker is not None:
        return "failed_provider", result, RebuildWorkflowBlocker(
            blocker_code="embedding_provider_failure",
            step_id="creating_embeddings",
            function_or_route="create_embeddings",
            recovery_state_class="support_only_unrecoverable",
            user_visible_summary="Embedding provider failed after Corpus Builder rebuild.",
            diagnostics=blocker.diagnostics,
        )
    output = _adapter_output(result)
    embedding_result = str(output.get("embedding_result") or "created").strip().casefold()
    if embedding_result in {"completed", "created", "ok"}:
        return "created", result, None
    if embedding_result in {"disabled", "skipped", "skipped_unconfigured"}:
        if embedding_policy == DEFAULT_EMBEDDING_POLICY:
            return "skipped_unconfigured", result, None
        return "failed_provider", result, RebuildWorkflowBlocker(
            blocker_code="embedding_provider_unavailable",
            step_id="creating_embeddings",
            function_or_route="create_embeddings",
            recovery_state_class="support_only_unrecoverable",
            user_visible_summary="Embedding provider configuration is required for this rebuild.",
        )
    return embedding_result or "created", result, None
