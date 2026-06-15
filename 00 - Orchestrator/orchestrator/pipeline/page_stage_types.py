"""Page-scoped pipeline work item types."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class PageStageResult:
    ok: bool
    path: Path | None = None
    request_path: Path | None = None
    reason: str = ""
    retry_from: str = ""
    status: str = ""
    needs_review: bool = False
    review_stage: str = ""
    review_reason: str = ""

    @classmethod
    def success(
        cls,
        path: Path | None = None,
        *,
        request_path: Path | None = None,
        status: str = "",
        needs_review: bool = False,
        review_stage: str = "",
        review_reason: str = "",
    ) -> "PageStageResult":
        return cls(
            ok=True,
            path=path,
            request_path=request_path,
            status=status,
            needs_review=needs_review,
            review_stage=review_stage,
            review_reason=review_reason,
        )

    @classmethod
    def failure(
        cls,
        reason: str,
        *,
        path: Path | None = None,
        request_path: Path | None = None,
        retry_from: str = "",
        status: str = "",
    ) -> "PageStageResult":
        return cls(
            ok=False,
            path=path,
            request_path=request_path,
            reason=str(reason or "").strip(),
            retry_from=retry_from,
            status=status,
        )


@dataclass(slots=True)
class PageWorkItem:
    active: Any
    page_index: int
    page_total: int
    raw_path: Path
    request_path: Path | None = None
    interpreter_debug_bundle_path: Path | None = None
    structured_path: Path | None = None
    validation_path: Path | None = None
    normalizer_request_path: Path | None = None
    normalized_path: Path | None = None
    failed_attempts: int = 0
    last_stage: str = ""
    last_error: str = ""
    terminal: bool = False
    succeeded: bool = False

    @property
    def record(self) -> Any:
        return self.active.record

    @property
    def paths(self) -> Any:
        return self.active.paths

    @property
    def page_number(self) -> int:
        return self.page_index + 1

    @property
    def label(self) -> str:
        if self.page_total <= 1:
            return self.raw_path.name
        return f"Page {self.page_number}/{self.page_total}"
