from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.adapters.orchestrator_llm import OrchestratorHostedLLMAdapter
from semantic_control_kernel.workflows.llm_calls.runner import LLMCallRunner
from semantic_control_kernel.workflows.llm_calls.runtime import RUNTIME_PROFILE_NAME


class KernelLLMPort:
    def __init__(
        self,
        *,
        state_root: str | Path,
        pipeline_root: str | Path | None = None,
        provider_adapter: OrchestratorHostedLLMAdapter | None = None,
    ) -> None:
        self.state_root = Path(state_root)
        self.provider_adapter = provider_adapter or OrchestratorHostedLLMAdapter(
            state_root=state_root,
            pipeline_root=pipeline_root,
        )

    def runtime_settings(self) -> dict[str, Any]:
        return self.provider_adapter.runtime_profile()

    def run(
        self,
        llm_function_name: str,
        *,
        workflow_run_id: str,
        analysis_run_id: str,
        input_payload: Any,
        runtime_settings: Mapping[str, Any] | None = None,
        preserved_state_summary: Mapping[str, Any] | None = None,
        artifact_root: str | Path | None = None,
    ):
        settings = _runtime_settings_or_profile(runtime_settings, self.provider_adapter)
        runner = LLMCallRunner(
            self.provider_adapter,
            artifact_root=artifact_root or self.state_root / "llm_calls",
            state_root=self.state_root,
        )
        return runner.run(
            llm_function_name,
            workflow_run_id=workflow_run_id,
            analysis_run_id=analysis_run_id,
            input_payload=input_payload,
            runtime_settings=settings,
            preserved_state_summary=preserved_state_summary,
        )


def _runtime_settings_or_profile(
    runtime_settings: Mapping[str, Any] | None,
    provider_adapter: OrchestratorHostedLLMAdapter,
) -> Mapping[str, Any]:
    if isinstance(runtime_settings, Mapping) and isinstance(runtime_settings.get(RUNTIME_PROFILE_NAME), Mapping):
        return runtime_settings
    return provider_adapter.runtime_profile()


__all__ = ["KernelLLMPort"]
