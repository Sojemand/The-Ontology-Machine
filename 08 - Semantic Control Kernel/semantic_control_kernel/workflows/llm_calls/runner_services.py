from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from semantic_control_kernel.policy.llm_retry_policy import LLMRetryPolicy
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.workflows.llm_calls.artifacts import LLMArtifactStore
from semantic_control_kernel.workflows.llm_calls.completed_attempts import CompletedAttemptHandler
from semantic_control_kernel.workflows.llm_calls.diagnostics import LLMAttemptDiagnosticSink
from semantic_control_kernel.workflows.llm_calls.final_errors import LLMFinalErrorBuilder
from semantic_control_kernel.workflows.llm_calls.provider_failures import ProviderFailureHandler


@dataclass(frozen=True)
class LLMCallRunnerServices:
    artifacts: LLMArtifactStore
    retry_policy: LLMRetryPolicy
    state_paths: StatePaths | None
    diagnostics: LLMAttemptDiagnosticSink
    final_errors: LLMFinalErrorBuilder
    completed_attempts: CompletedAttemptHandler
    provider_failures: ProviderFailureHandler


def create_runner_services(
    *,
    artifact_root: str | Path,
    state_root: str | Path | None,
    retry_policy: LLMRetryPolicy | None,
) -> LLMCallRunnerServices:
    artifacts = LLMArtifactStore(artifact_root)
    resolved_retry_policy = retry_policy or LLMRetryPolicy()
    state_paths = StatePaths.from_state_root(state_root) if state_root is not None else None
    diagnostics = LLMAttemptDiagnosticSink.from_state_paths(state_paths)
    final_errors = LLMFinalErrorBuilder.from_state_paths(artifacts, state_paths)
    completed_attempts = CompletedAttemptHandler(
        artifacts=artifacts,
        retry_policy=resolved_retry_policy,
        diagnostics=diagnostics,
    )
    provider_failures = ProviderFailureHandler(
        artifacts=artifacts,
        retry_policy=resolved_retry_policy,
        diagnostics=diagnostics,
        final_errors=final_errors,
    )
    return LLMCallRunnerServices(
        artifacts=artifacts,
        retry_policy=resolved_retry_policy,
        state_paths=state_paths,
        diagnostics=diagnostics,
        final_errors=final_errors,
        completed_attempts=completed_attempts,
        provider_failures=provider_failures,
    )
