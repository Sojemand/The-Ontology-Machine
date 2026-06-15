from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.adapters.base import BasePipelineAdapter, READ_ONLY_TIMEOUT_SECONDS, SHORT_WRITE_TIMEOUT_SECONDS
from semantic_control_kernel.types.adapter_results import AdapterCallResult, MissingCapabilityBlocker


MERGE_PREFLIGHT_TIMEOUT_SECONDS = 1000
MERGE_WRITE_TIMEOUT_SECONDS = 1000


class MergeAdapter(BasePipelineAdapter):
    adapter_name = "MergeAdapter"

    def multi_source_merge_preflight(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult | MissingCapabilityBlocker:
        payload = dict(request_payload or {})
        selection = payload.get("selection") if isinstance(payload.get("selection"), Mapping) else None
        if selection is None:
            return self._missing("database_merge_additive_only")
        return self._invoke_corpus("multi_source_merge_preflight", "database_merge_additive_only", payload, read_only=True)

    def merge_empty_databases(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult | MissingCapabilityBlocker:
        payload = dict(request_payload or {})
        if not isinstance(payload.get("selection"), Mapping):
            return self._missing("merge_database_empty")
        payload.setdefault("mode", "additive")
        return self._invoke_corpus("multi_source_merge_databases", "merge_database_empty", payload)

    def merge_filled_databases(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult | MissingCapabilityBlocker:
        payload = dict(request_payload or {})
        if not isinstance(payload.get("selection"), Mapping):
            return self._missing("merge_database_filled_additive")
        payload.setdefault("mode", "additive")
        return self._invoke_corpus("multi_source_merge_databases", "merge_database_filled_additive", payload)

    def merge_semantic_release_candidates(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult | MissingCapabilityBlocker:
        payload = dict(request_payload or {})
        source_releases = payload.get("source_releases")
        if not isinstance(source_releases, list):
            return self._missing("merge_taxonomy_and_projections_additive")
        return self._invoke_normalizer("merge_semantic_release_candidates", "merge_taxonomy_and_projections_additive", payload)

    def write_merge_reconciliation_manifest(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult | MissingCapabilityBlocker:
        payload = dict(request_payload or {})
        if not payload:
            return self._missing("reconcile_merged_database")
        return self._invoke_corpus(
            "write_merge_reconciliation_manifest",
            "reconcile_merged_database",
            payload,
            required_target_proof_fields=("merge_run_id", "target_database_path_hash"),
        )

    def write_combined_database(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult | MissingCapabilityBlocker:
        return self._compatibility_only(
            "write_combined_database",
            "Target SQL is written by merge_database_filled_additive through multi_source_merge_databases.",
        )

    def fill_artifact_tree(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult | MissingCapabilityBlocker:
        return self._compatibility_only(
            "fill_artifact_folder_tree",
            "Target artifacts are copied by merge_database_filled_additive through multi_source_merge_databases.",
        )

    def _missing(self, kernel_function: str) -> AdapterCallResult:
        return self.blocked_by_kernel_precondition(
            kernel_function=kernel_function,
            capability_status="implemented_in_pipeline",
            summary=f"{kernel_function} requires an explicit merge selection payload.",
            missing_fields=("selection",),
        )

    def _compatibility_only(self, kernel_function: str, summary: str) -> AdapterCallResult:
        return self.blocked_by_kernel_precondition(
            kernel_function=kernel_function,
            capability_status="kernel_internal_no_pipeline_adapter",
            summary=summary,
            missing_fields=(),
        )

    def _invoke_corpus(
        self,
        owner_action: str,
        kernel_function: str,
        payload: Mapping[str, Any],
        *,
        read_only: bool = False,
        required_target_proof_fields: tuple[str, ...] | None = None,
    ) -> AdapterCallResult:
        selection = payload.get("selection") if isinstance(payload.get("selection"), Mapping) else {}
        target_identity = _merge_target_identity(self, payload, selection)
        target_proof_fields = required_target_proof_fields or ("merge_run_id", "source_database_ids", "target_database_path_hash")
        owner_request = self.phase19_request(
            owner_action=owner_action,
            request_payload=payload,
            target_identity=target_identity,
            **{key: value for key, value in dict(payload).items() if key != "target_identity"},
        )
        return self.invoke(
            kernel_function=kernel_function,
            owner_module="05 - Corpus Builder",
            owner_contract_module="corpus_builder.orchestrator_contract",
            owner_action=owner_action,
            request_payload=owner_request,
            capability_status="implemented_in_pipeline",
            timeout_seconds=_corpus_timeout_seconds(owner_action, read_only=read_only),
            mutating=not read_only,
            required_target_proof_fields=() if read_only else target_proof_fields,
            target_identity=target_identity,
        )

    def _invoke_normalizer(self, owner_action: str, kernel_function: str, payload: Mapping[str, Any], *, read_only: bool = False) -> AdapterCallResult:
        selection = payload.get("selection") if isinstance(payload.get("selection"), Mapping) else {}
        target_identity = {"merge_run_id": str(payload.get("merge_run_id") or selection.get("merge_run_id") or "")}
        owner_request = self.phase19_request(
            owner_action=owner_action,
            request_payload=payload,
            target_identity=target_identity,
            **{key: value for key, value in dict(payload).items() if key != "target_identity"},
        )
        return self.invoke(
            kernel_function=kernel_function,
            owner_module="04 - Normalizer",
            owner_contract_module="normalizer_vision.edit_contract",
            owner_action=owner_action,
            request_payload=owner_request,
            capability_status="implemented_in_pipeline",
            timeout_seconds=READ_ONLY_TIMEOUT_SECONDS if read_only else SHORT_WRITE_TIMEOUT_SECONDS,
            mutating=not read_only,
            required_target_proof_fields=() if read_only else ("merge_run_id", "release_fingerprint"),
            target_identity=target_identity,
        )


def _merge_target_identity(adapter: MergeAdapter, payload: Mapping[str, Any], selection: Mapping[str, Any]) -> dict[str, Any]:
    manifest = payload.get("collision_manifest") if isinstance(payload.get("collision_manifest"), Mapping) else {}
    target_database_path = str(
        payload.get("target_database_path")
        or selection.get("target_database_path")
        or manifest.get("target_database_path")
        or ""
    )
    target_database_path_hash = str(payload.get("target_database_path_hash") or selection.get("target_database_path_hash") or "")
    if not target_database_path_hash and target_database_path:
        target_database_path_hash = adapter.owner_path_hash(target_database_path)
    source_database_ids = _source_database_ids(payload, selection)
    return adapter.target_identity(
        payload,
        merge_run_id=str(payload.get("merge_run_id") or selection.get("merge_run_id") or ""),
        extra={
            "source_database_ids": source_database_ids,
            "target_database_path_hash": target_database_path_hash,
        },
    )


def _source_database_ids(payload: Mapping[str, Any], selection: Mapping[str, Any]) -> list[str]:
    direct = payload.get("source_database_ids")
    if isinstance(direct, list):
        return [str(item) for item in direct if str(item)]
    sources = selection.get("source_databases", payload.get("source_databases", []))
    if not isinstance(sources, list):
        return []
    return [
        str(item.get("source_database_id"))
        for item in sources
        if isinstance(item, Mapping) and item.get("source_database_id")
    ]


def _corpus_timeout_seconds(owner_action: str, *, read_only: bool) -> int:
    if read_only:
        return MERGE_PREFLIGHT_TIMEOUT_SECONDS
    if owner_action == "multi_source_merge_databases":
        return MERGE_WRITE_TIMEOUT_SECONDS
    return SHORT_WRITE_TIMEOUT_SECONDS
