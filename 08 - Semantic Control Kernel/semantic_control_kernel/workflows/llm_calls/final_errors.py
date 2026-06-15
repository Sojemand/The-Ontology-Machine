from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.debug.redaction import RedactionEngine, RedactionProfile
from semantic_control_kernel.debug.support_bundle_builder import SupportBundleBuilder
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.support_bundles import SupportBundleStore
from semantic_control_kernel.types.llm_calls import LLMFinalError
from semantic_control_kernel.workflows.llm_calls.artifacts import LLMArtifactStore
from semantic_control_kernel.workflows.llm_calls.function_registry import get_llm_function_definition
from semantic_control_kernel.workflows.llm_calls.recovery_options import final_recovery_options
from semantic_control_kernel.workflows.llm_calls.result_events import final_mirror_event


class LLMFinalErrorBuilder:
    def __init__(
        self,
        artifacts: LLMArtifactStore,
        *,
        support_bundle_builder: SupportBundleBuilder | None = None,
        support_redaction: RedactionEngine | None = None,
    ) -> None:
        self.artifacts = artifacts
        self.support_bundle_builder = support_bundle_builder
        self.support_redaction = support_redaction

    @classmethod
    def from_state_paths(cls, artifacts: LLMArtifactStore, state_paths: StatePaths | None) -> "LLMFinalErrorBuilder":
        if state_paths is None:
            return cls(artifacts)
        return cls(
            artifacts,
            support_bundle_builder=SupportBundleBuilder(SupportBundleStore(state_paths)),
            support_redaction=RedactionEngine(state_root=state_paths.state_root),
        )

    def validation_failure(
        self,
        *,
        definition_name: str,
        workflow_run_id: str,
        analysis_run_id: str,
        attempted_schema: str,
        attempts_used: int,
        validation_error_summary: str,
        failed_attempt_refs: tuple[Mapping[str, Any], ...],
        failed_attempt_diagnostic_refs: tuple[Mapping[str, Any], ...],
        preserved_state_summary: Mapping[str, Any],
    ) -> tuple[LLMFinalError, dict[str, Any]]:
        recovery_options, allowed_tools = final_recovery_options(preserved_state_summary)
        definition = get_llm_function_definition(definition_name)
        support_path = definition.run_folder_template.format(analysis_run_id=analysis_run_id)
        artifact_support_bundle_ref = {
            "support_bundle_id": f"support_{definition_name}_{analysis_run_id}",
            "artifact_path": f"{support_path}/s/bundle.json",
        }
        final_error = LLMFinalError(
            error_code="llm_validation_exhausted",
            category="llm_validation",
            llm_function_name=definition_name,
            workflow_run_id=workflow_run_id,
            analysis_run_id=analysis_run_id,
            attempted_schema=attempted_schema,
            attempts_used=attempts_used,
            failed_attempt_artifact_refs=failed_attempt_refs,
            support_bundle_ref=artifact_support_bundle_ref,
            validation_error_summary=validation_error_summary,
            preserved_state_summary=preserved_state_summary,
            recovery_options=tuple(recovery_options),
            allowed_agent_tools=tuple(allowed_tools),
        )
        artifact_support_bundle_ref = self.artifacts.write_support_bundle(
            definition,
            analysis_run_id,
            final_error.to_dict(),
        )
        state_support_bundle_ref = None
        if self.support_bundle_builder is not None and self.support_redaction is not None:
            state_support_bundle_ref = self.support_bundle_builder.build_for_final_llm_validation_failure(
                workflow_run_id=workflow_run_id,
                category="final_llm_validation_failure",
                severity="final_error",
                safe_summary="The Kernel could not obtain valid structured JSON for the isolated LLM function after the retry budget was exhausted.",
                user_visible_cause=validation_error_summary,
                redaction_profile=self.support_redaction.profile_payload(RedactionProfile.SUPPORT_SAFE_V1),
                included_refs=failed_attempt_refs,
                workflow_tool=definition_name,
                llm_attempt_diagnostic_refs=failed_attempt_diagnostic_refs,
                failed_attempt_artifact_refs=failed_attempt_refs,
                created_by="llm_call_runner",
            ).to_dict()
        final_error = LLMFinalError(
            error_code="llm_validation_exhausted",
            category="llm_validation",
            llm_function_name=definition_name,
            workflow_run_id=workflow_run_id,
            analysis_run_id=analysis_run_id,
            attempted_schema=attempted_schema,
            attempts_used=attempts_used,
            failed_attempt_artifact_refs=failed_attempt_refs,
            support_bundle_ref=state_support_bundle_ref or artifact_support_bundle_ref,
            validation_error_summary=validation_error_summary,
            preserved_state_summary=preserved_state_summary,
            recovery_options=tuple(recovery_options),
            allowed_agent_tools=tuple(allowed_tools),
        )
        mirror_event = final_mirror_event(final_error, "llm_validation_failed_final", "final_error")
        return final_error, mirror_event

    def provider_failure(
        self,
        *,
        definition_name: str,
        workflow_run_id: str,
        analysis_run_id: str,
        attempted_schema: str,
        attempts_used: int,
        provider_status: str,
        provider_message: str,
        failed_attempt_refs: tuple[Mapping[str, Any], ...],
        preserved_state_summary: Mapping[str, Any],
    ) -> tuple[LLMFinalError, dict[str, Any]]:
        recovery_options, allowed_tools = final_recovery_options(preserved_state_summary)
        summary = f"Provider failure after retry budget: {provider_status}."
        if provider_message:
            summary = f"Provider failure after retry budget: {provider_status}: {provider_message}"
        support_bundle_ref = self.artifacts.write_support_bundle(
            get_llm_function_definition(definition_name),
            analysis_run_id,
            {
                "category": "llm_provider",
                "provider_status": provider_status,
                "provider_error_summary": summary,
                "failed_attempt_artifact_refs": list(failed_attempt_refs),
            },
        )
        final_error = LLMFinalError(
            error_code=provider_status,
            category="llm_provider",
            llm_function_name=definition_name,
            workflow_run_id=workflow_run_id,
            analysis_run_id=analysis_run_id,
            attempted_schema=attempted_schema,
            attempts_used=attempts_used,
            failed_attempt_artifact_refs=failed_attempt_refs,
            support_bundle_ref=support_bundle_ref,
            validation_error_summary=summary,
            preserved_state_summary=preserved_state_summary,
            recovery_options=tuple(recovery_options),
            allowed_agent_tools=tuple(allowed_tools),
        )
        mirror_event = final_mirror_event(final_error, "pipeline_error", "final_error")
        return final_error, mirror_event
