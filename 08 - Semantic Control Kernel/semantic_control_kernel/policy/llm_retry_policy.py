from __future__ import annotations

from dataclasses import dataclass
import re


TRANSIENT_PROVIDER_FAILURES = frozenset(
    {
        "timeout",
        "rate_limit",
        "rate_limited",
        "server_error",
        "transient_error",
        "5xx",
    }
)

TRANSIENT_PROVIDER_ERROR_MESSAGE_RE = re.compile(
    r"(incompleteread|connection\s+reset|remote\s+connection|disconnect|read\s+timed\s+out|timeout|timed\s+out|broken\s+pipe)",
    re.IGNORECASE,
)

BLOCKING_PROVIDER_FAILURES = frozenset(
    {
        "llm_runtime_missing",
        "credentials_missing",
        "invalid_model_profile",
        "host_capability_missing",
        "auth_missing",
        "unauthorized",
    }
)


@dataclass(frozen=True)
class LLMRetryPolicy:
    max_attempts: int = 3
    retry_policy_ref: str = "phase8.llm_retry_policy.v1"

    def should_retry_validation_failure(self, attempt_index: int) -> bool:
        return attempt_index < self.max_attempts

    def should_retry_provider_failure(self, status: str, attempt_index: int, message: str = "") -> bool:
        return self.is_transient_provider_failure(status, message) and attempt_index < self.max_attempts

    def is_blocking_provider_failure(self, status: str) -> bool:
        return status in BLOCKING_PROVIDER_FAILURES

    def is_transient_provider_failure(self, status: str, message: str = "") -> bool:
        if status in TRANSIENT_PROVIDER_FAILURES:
            return True
        if status != "provider_error":
            return False
        return bool(TRANSIENT_PROVIDER_ERROR_MESSAGE_RE.search(str(message or "")))

    def next_action_for_validation(self, attempt_index: int) -> str:
        if self.should_retry_validation_failure(attempt_index):
            return "retry_with_compact_validation_feedback"
        return "emit_final_llm_validation_failure"

    def next_action_for_provider_failure(self, status: str, attempt_index: int, message: str = "") -> str:
        if self.should_retry_provider_failure(status, attempt_index, message):
            return "retry_provider_transient_failure"
        if self.is_blocking_provider_failure(status):
            return "block_before_provider_execution"
        return "emit_final_llm_provider_failure"
