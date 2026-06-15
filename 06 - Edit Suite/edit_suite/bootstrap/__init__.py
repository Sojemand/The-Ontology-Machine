"""Path-stable bootstrap surface for the Edit Suite."""

from .types import StartupContext, StartupPrerequisiteError
from .workflow import EDIT_SUITE_ROOT, PIPELINE_ROOT, STATE_ROOT, ensure_startup_prerequisites

__all__ = [
    "EDIT_SUITE_ROOT",
    "PIPELINE_ROOT",
    "STATE_ROOT",
    "StartupContext",
    "StartupPrerequisiteError",
    "ensure_startup_prerequisites",
]
