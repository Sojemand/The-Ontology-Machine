from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from phase11_owner_output_fakes import owner_output, owner_output_for_request
from phase11_result_fakes import blocked_precondition, missing, ok_result


class FakeBatchAdapter:
    def __init__(
        self,
        *,
        missing_methods: Sequence[str] = (),
    ) -> None:
        self.missing_methods = set(missing_methods)
        self.calls: list[tuple[str, Mapping[str, Any]]] = []

    def create_batch_manifest(self, request_payload: Mapping[str, Any] | None = None):
        return self._result(
            "create_batch_manifest",
            request_payload,
            required_fields=("workflow_run_id", "pipeline_batch_id", "artifact_root", "active_database", "semantic_release", "input_files"),
        )

    def finalize_batch_manifest(self, request_payload: Mapping[str, Any] | None = None):
        return self._result(
            "finalize_batch_manifest",
            request_payload,
            required_fields=("workflow_run_id", "pipeline_batch_id", "artifact_root", "pending_manifest_ref", "record_counts", "materialized_records", "correlation_report"),
        )

    def _result(
        self,
        method_name: str,
        request_payload: Mapping[str, Any] | None,
        *,
        required_fields: Sequence[str] = (),
    ):
        if method_name in self.missing_methods:
            return missing(method_name)
        missing_fields = self._missing_fields(request_payload, required_fields)
        if missing_fields:
            return blocked_precondition(
                method_name,
                missing_fields=missing_fields,
                summary=f"{method_name} is missing required owner-domain evidence.",
            )
        self.calls.append((method_name, dict(request_payload or {})))
        return ok_result(method_name, {"accepted": True})

    @staticmethod
    def _missing_fields(request_payload: Mapping[str, Any] | None, fields: Sequence[str]) -> list[str]:
        payload = dict(request_payload or {})
        missing_fields: list[str] = []
        for field in fields:
            value = payload.get(field)
            if value in (None, "", [], {}):
                missing_fields.append(field)
        return missing_fields


class FakeOrchestratorAdapter:
    def __init__(
        self,
        output_refs: Mapping[str, Any] | None = None,
        *,
        enrich_materialization_refs: bool = True,
    ) -> None:
        self.output_refs = dict(output_refs or owner_output())
        self.enrich_materialization_refs = enrich_materialization_refs
        self.calls: list[Mapping[str, Any]] = []
        self.reset_error_cases_calls: list[Mapping[str, Any]] = []

    def run_pipeline(self, request_payload: Mapping[str, Any] | None = None, *, progress_callback=None):
        payload = dict(request_payload or {})
        self.calls.append(payload)
        if progress_callback is not None:
            progress_callback()
        missing_fields = [
            field
            for field in ("pipeline_batch_id", "input_files", "active_database", "semantic_release")
            if payload.get(field) in (None, "", [], {})
        ]
        if missing_fields:
            return blocked_precondition(
                "pipeline_run",
                missing_fields=missing_fields,
                summary="pipeline_run requires explicit batch, input and target evidence.",
            )
        output = deepcopy(self.output_refs)
        if self.enrich_materialization_refs:
            output = owner_output_for_request(payload, output=output)
        return ok_result("pipeline_run", output)

    def reset_error_cases(self, request_payload: Mapping[str, Any] | None = None):
        payload = dict(request_payload or {})
        self.reset_error_cases_calls.append(payload)
        return ok_result("manual_pipeline_run", {"reset_error_cases": True})


class FakeCorpusAdapter:
    def __init__(
        self,
        *,
        preserve: bool = True,
        empty_state_proven: bool = True,
        target_identity_after: Mapping[str, Any] | None = None,
    ) -> None:
        self.preserve = preserve
        self.empty_state_proven = empty_state_proven
        self.target_identity_after = dict(target_identity_after) if isinstance(target_identity_after, Mapping) else None
        self.calls: list[Mapping[str, Any]] = []

    def reset_database(self, request_payload: Mapping[str, Any] | None = None):
        self.calls.append(dict(request_payload or {}))
        return ok_result(
            "reset_database",
            {
                "semantic_release_preserved": self.preserve,
                "empty_state_proven": self.empty_state_proven,
                "target_identity_after": self.target_identity_after or dict((request_payload or {}).get("target_identity", {})),
            },
        )
