from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.domain.recovery.semantic_exception_handler import UnexpectedKernelException


def support_only_exception(cause_code: str, user_visible_cause: str, technical_context: Mapping[str, Any] | None = None) -> UnexpectedKernelException:
    return UnexpectedKernelException(
        cause_code=cause_code,
        user_visible_cause=user_visible_cause,
        technical_context=dict(technical_context or {}),
    )
