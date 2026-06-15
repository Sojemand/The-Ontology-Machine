"""Bootstrap datatypes for the Edit Suite."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class StartupPrerequisiteError(RuntimeError):
    """Raised when suite-local startup prerequisites are not met."""


@dataclass(frozen=True)
class StartupContext:
    module_root: Path
    pipeline_root: Path
    state_root: Path
