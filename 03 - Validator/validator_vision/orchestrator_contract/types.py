"""Named contract types shared between subprocess stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

VALIDATE_DOCUMENT_ACTION = "validate_document"
HEALTHCHECK_ACTION = "healthcheck"
DEBUG_RUN_ACTION = "debug_run"
ActionName = Literal["validate_document", "healthcheck", "debug_run"]


@dataclass(frozen=True)
class ValidateDocumentCommand:
    structured_path: Path
    validation_output_path: Path
    raw_path: Path | None = None


@dataclass(frozen=True)
class DebugRunCommand:
    mode: Literal["single", "batch"]
    session_root: Path
    output_root: Path
    source_path: Path | None = None
    input_root: Path | None = None
    raw_path: Path | None = None
    raw_root: Path | None = None
    check_toggles: dict[str, bool] = field(default_factory=dict)
