from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from semantic_control_kernel.types.enums import ProgressEventType, ProgressStatus


ProgressEmitter = Callable[[Mapping[str, Any]], None]
ProgressAppender = Callable[..., Any]


class ProgressReportingLLMPort:
    def __init__(self, delegate: Any, *, emit_progress: ProgressEmitter, step_id_prefix: str = "llm") -> None:
        self._delegate = delegate
        self._emit_progress = emit_progress
        self._step_id_prefix = step_id_prefix.strip("_") or "llm"

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
        progress_failure_mode: str | None = None,
        **kwargs: Any,
    ) -> Any:
        self._emit(
            llm_function_name,
            analysis_run_id=analysis_run_id,
            status=ProgressStatus.STEP_STARTED.value,
            summary=f"LLM call {llm_function_name} started via Orchestrator/Interpreter.",
        )
        try:
            result = self._run_delegate(
                llm_function_name,
                workflow_run_id=workflow_run_id,
                analysis_run_id=analysis_run_id,
                input_payload=input_payload,
                runtime_settings=runtime_settings,
                preserved_state_summary=preserved_state_summary,
                artifact_root=artifact_root,
                **kwargs,
            )
        except Exception:
            self._emit(
                llm_function_name,
                analysis_run_id=analysis_run_id,
                status=ProgressStatus.FAILED.value,
                summary=f"LLM call {llm_function_name} failed before the Kernel could validate output.",
            )
            raise
        self._emit_result(
            llm_function_name,
            analysis_run_id=analysis_run_id,
            result=result,
            progress_failure_mode=progress_failure_mode,
        )
        return result

    def _run_delegate(self, llm_function_name: str, **kwargs: Any) -> Any:
        run = getattr(self._delegate, "run", None)
        if callable(run):
            try:
                return run(llm_function_name, **kwargs)
            except TypeError:
                if "artifact_root" in kwargs:
                    fallback_kwargs = dict(kwargs)
                    fallback_kwargs.pop("artifact_root", None)
                    return run(llm_function_name, **fallback_kwargs)
                raise
        method = getattr(self._delegate, llm_function_name)
        return method(**kwargs)

    def _emit_result(
        self,
        llm_function_name: str,
        *,
        analysis_run_id: str,
        result: Any,
        progress_failure_mode: str | None = None,
    ) -> None:
        status = str(getattr(result, "status", "") or "unknown")
        attempts = int(getattr(result, "attempts_used", 0) or 0)
        artifact_ref = getattr(result, "output_artifact_ref", None)
        refs = [_llm_ref(llm_function_name, analysis_run_id, attempts)]
        if isinstance(artifact_ref, Mapping):
            refs.append(dict(artifact_ref))
        if bool(getattr(result, "succeeded", False)):
            self._emit(
                llm_function_name,
                analysis_run_id=analysis_run_id,
                status=ProgressStatus.COMPLETED.value,
                summary=f"LLM call {llm_function_name} completed{_attempt_text(attempts)}.",
                artifact_refs=refs,
            )
            return
        if progress_failure_mode == "optional_unavailable":
            self._emit(
                llm_function_name,
                analysis_run_id=analysis_run_id,
                status=ProgressStatus.COMPLETED.value,
                summary=f"Optional LLM call {llm_function_name} unavailable with {status}{_attempt_text(attempts)}; continuing.",
                artifact_refs=refs,
            )
            return
        self._emit(
            llm_function_name,
            analysis_run_id=analysis_run_id,
            status=ProgressStatus.FAILED.value,
            summary=f"LLM call {llm_function_name} finished with {status}{_attempt_text(attempts)}.",
            artifact_refs=refs,
        )

    def _emit(
        self,
        llm_function_name: str,
        *,
        analysis_run_id: str,
        status: str,
        summary: str,
        artifact_refs: list[Mapping[str, Any]] | None = None,
    ) -> None:
        self._emit_progress(
            {
                "step_id": f"{self._step_id_prefix}_{llm_function_name}",
                "status": status,
                "summary": summary,
                "artifact_refs": artifact_refs or [_llm_ref(llm_function_name, analysis_run_id, 0)],
            }
        )


def progress_reporting_llm_port(
    delegate: Any,
    *,
    append_progress: ProgressAppender,
    step_id_prefix: str = "llm",
) -> ProgressReportingLLMPort:
    def emit_progress(event: Mapping[str, Any]) -> None:
        append_progress(
            step_id=str(event.get("step_id") or "llm_call"),
            status=str(event.get("status") or ProgressStatus.COMPLETED.value),
            summary=str(event.get("summary") or "LLM call progress."),
            event_type=ProgressEventType.LLM_STEP.value,
            artifact_refs=tuple(item for item in (event.get("artifact_refs") or ()) if isinstance(item, Mapping)),
        )

    return ProgressReportingLLMPort(delegate, emit_progress=emit_progress, step_id_prefix=step_id_prefix)


def _llm_ref(llm_function_name: str, analysis_run_id: str, attempts: int) -> dict[str, Any]:
    return {
        "artifact_kind": "llm_call",
        "llm_function_name": llm_function_name,
        "analysis_run_id": analysis_run_id,
        "attempts_used": attempts,
    }


def _attempt_text(attempts: int) -> str:
    if attempts <= 0:
        return ""
    return f" after {attempts} attempt{'s' if attempts != 1 else ''}"
