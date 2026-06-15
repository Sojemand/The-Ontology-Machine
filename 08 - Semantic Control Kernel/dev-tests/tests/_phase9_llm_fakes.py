from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from semantic_control_kernel.types.llm_calls import LLMCallResult

from _phase9_support import load_llm_fixtures


class FakeLLMPort:
    def __init__(self, *, fail_final: str | None = None) -> None:
        self.fixtures = load_llm_fixtures()
        self.fail_final = fail_final
        self.calls: list[tuple[str, Any]] = []
        self.artifact_roots: list[tuple[str, str]] = []

    def run(
        self,
        function_name: str,
        *,
        workflow_run_id: str,
        analysis_run_id: str,
        input_payload: Mapping[str, Any],
        runtime_settings: Mapping[str, Any] | None = None,
        preserved_state_summary: Mapping[str, Any] | None = None,
        artifact_root: str | Path | None = None,
    ) -> LLMCallResult:
        self.calls.append((function_name, deepcopy(input_payload)))
        if artifact_root is not None:
            self.artifact_roots.append((function_name, str(artifact_root)))
        if self.fail_final == function_name:
            return LLMCallResult(
                status="failed_final_validation",
                llm_function_name=function_name,
                workflow_run_id=workflow_run_id,
                analysis_run_id=analysis_run_id,
            )
        outputs = {
            "analyze_samples": self._sample_analysis_output(input_payload),
            "user_report_samples": self._report_output("Sample analysis report."),
            "create_taxonomy_to_sample_analyses": self._taxonomy_proposal_output(input_payload),
            "create_projections_to_sample_analyses": self._projection_proposal_output(input_payload),
        }
        return LLMCallResult(
            status="succeeded",
            llm_function_name=function_name,
            workflow_run_id=workflow_run_id,
            analysis_run_id=analysis_run_id,
            output=outputs[function_name],
            output_artifact_ref={"artifact_path": f"{analysis_run_id}/{function_name}.json"},
            attempts_used=1,
        )

    def _sample_analysis_output(self, input_payload: Mapping[str, Any] | Sequence[Any]) -> dict[str, Any]:
        output = deepcopy(self.fixtures["sample_analyses"])
        if isinstance(input_payload, (list, tuple)):
            sample_ids = [
                str(item.get("sample_id"))
                for item in input_payload
                if isinstance(item, Mapping) and item.get("sample_id")
            ]
            if sample_ids:
                output["sample_set"]["sample_ids"] = sample_ids
        return output

    def _taxonomy_proposal_output(self, input_payload: Mapping[str, Any] | Sequence[Any]) -> dict[str, Any]:
        output = deepcopy(self.fixtures["taxonomy_to_sample_analyses"])
        sample_analyses = input_payload.get("sample_analyses") if isinstance(input_payload, Mapping) else None
        if isinstance(sample_analyses, Mapping):
            sample_ids = sample_analyses.get("sample_set", {}).get("sample_ids")
            if isinstance(sample_ids, list):
                output["sample_ids"] = list(sample_ids)
        return output

    def _projection_proposal_output(self, input_payload: Mapping[str, Any] | Sequence[Any]) -> dict[str, Any]:
        output = deepcopy(self.fixtures["projections_to_sample_analyses"])
        if not isinstance(input_payload, Mapping):
            return output
        sample_analyses = input_payload.get("sample_analyses")
        if isinstance(sample_analyses, Mapping):
            sample_ids = sample_analyses.get("sample_set", {}).get("sample_ids")
            if isinstance(sample_ids, list):
                output["sample_ids"] = list(sample_ids)
        authoring_view = input_payload.get("taxonomy_authoring_view")
        if isinstance(authoring_view, Mapping) and isinstance(authoring_view.get("taxonomy_ref"), Mapping):
            output["taxonomy_ref"] = dict(authoring_view["taxonomy_ref"])
        return output

    def _report_output(self, prefix: str) -> str:
        return f"{prefix}\n\nGenerated for the active Pipeline session."
