from __future__ import annotations

import json

from pathlib import Path

import pytest

from normalizer_vision.models import NormalizationResult, NormalizerRuntimeSettings

from normalizer_vision.orchestrator_contract import validation, workflow

PROJECT_ROOT = Path(__file__).resolve().parents[2]

class _DummyNormalizer:
    def __init__(self, session_root: Path | None = None):
        self._session_root = session_root
        self.config = type(
            "Config",
            (),
            {
                "default_workers": 2,
                "max_batch_workers": 4,
                "max_batch_files": 50,
            },
        )()

    def normalize(self, structured_path: Path, normalized_output_path: Path) -> NormalizationResult:
        status = "ERROR" if structured_path.name.startswith("bad") else "OK"
        needs_review = structured_path.name.startswith("review")
        if status == "OK":
            normalized_output_path.parent.mkdir(parents=True, exist_ok=True)
            normalized_output_path.write_text("{}", encoding="utf-8")
        if self._session_root is not None and structured_path.name.startswith("cancel"):
            (self._session_root / "cancel.request").touch()
        return NormalizationResult(
            input_path=str(structured_path),
            output_path=str(normalized_output_path) if status == "OK" else None,
            status=status,
            needs_review=needs_review or status == "ERROR",
            duration_ms=12,
            message="broken" if status == "ERROR" else "normalized",
            review_reason="manual" if needs_review else "",
        )

__all__ = [name for name in globals() if not name.startswith("__")]
