from __future__ import annotations

from dataclasses import dataclass


KERNEL_BOOKKEEPING = "kernel_repository_bookkeeping"
PHASE6_INTERACTION = "phase_6_interaction"
SPEC04_LLM_TRANSITION = "spec_04_llm_artifact_transition"
SPEC11_DETERMINISTIC_TRANSFORM = "spec_11_deterministic_transformation"
READ_BUILD_SOURCE_STEP = "read_build_source_step"


@dataclass(frozen=True)
class DatabaseCreationStep:
    step_id: str
    operation: str
    transition_rule: str
    adapter_or_port: str
    required_state_or_evidence: str
    writes_or_artifacts: str
    progress_event: str
    resume_point: str

    @property
    def is_kernel_bookkeeping(self) -> bool:
        return self.transition_rule == KERNEL_BOOKKEEPING

    @property
    def is_state_changing(self) -> bool:
        return self.writes_or_artifacts not in {"none", "taxonomy ref in workflow state"}

    def to_dict(self) -> dict[str, str]:
        return {
            "step_id": self.step_id,
            "operation": self.operation,
            "transition_rule": self.transition_rule,
            "adapter_or_port": self.adapter_or_port,
            "required_state_or_evidence": self.required_state_or_evidence,
            "writes_or_artifacts": self.writes_or_artifacts,
            "progress_event": self.progress_event,
            "resume_point": self.resume_point,
        }


@dataclass(frozen=True)
class DatabaseCreationRoute:
    workflow_tool: str
    step_ids: tuple[str, ...]
    final_state: str
    continuation_semantics: str
    optional_step_ids: tuple[str, ...] = ()

    def sequence(self, *, include_optional: bool = False) -> tuple[str, ...]:
        if not include_optional or not self.optional_step_ids:
            return self.step_ids
        if self.step_ids and self.step_ids[-1] == "dc_final_notice":
            return self.step_ids[:-1] + self.optional_step_ids + ("dc_final_notice",)
        return self.step_ids + self.optional_step_ids

    def to_dict(self) -> dict[str, object]:
        return {
            "workflow_tool": self.workflow_tool,
            "step_ids": list(self.step_ids),
            "final_state": self.final_state,
            "continuation_semantics": self.continuation_semantics,
            "optional_step_ids": list(self.optional_step_ids),
        }
