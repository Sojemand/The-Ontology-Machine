from __future__ import annotations

from typing import Any, Mapping


class RecoveryRetryPolicy:
    def can_retry_final_llm_failure(self, evidence: Mapping[str, Any]) -> bool:
        return all(
            bool(evidence.get(key))
            for key in (
                "safe_resume_point",
                "target_identity_matches",
                "input_hashes_match",
                "failed_call_isolated",
            )
        ) and not bool(evidence.get("downstream_mutation_consumed_invalid_output"))

    def retry_rejection_reason(self, evidence: Mapping[str, Any]) -> str:
        if self.can_retry_final_llm_failure(evidence):
            return ""
        if not evidence.get("safe_resume_point"):
            return "safe_resume_point_missing"
        if not evidence.get("target_identity_matches"):
            return "target_identity_changed"
        if not evidence.get("input_hashes_match"):
            return "input_hash_mismatch"
        if evidence.get("downstream_mutation_consumed_invalid_output"):
            return "downstream_mutation_consumed_invalid_output"
        return "failed_call_not_isolated"
