"""Path-stable surface for database merge source selection."""

from __future__ import annotations

from semantic_control_kernel.workflows.merge.source_selection_builder import build_database_merge_selection
from semantic_control_kernel.workflows.merge.source_selection_policy import (
    classify_merge_route,
    normalize_projection_merge_mode,
    projection_merge_mode_blocker,
    route_blocker_for_selection,
)
from semantic_control_kernel.workflows.merge.source_selection_resume import (
    load_existing_database_merge_selection,
    resume_database_merge_selection,
)
from semantic_control_kernel.workflows.merge.source_selection_target import target_confirmation_blocker

__all__ = [
    "build_database_merge_selection",
    "classify_merge_route",
    "load_existing_database_merge_selection",
    "normalize_projection_merge_mode",
    "projection_merge_mode_blocker",
    "resume_database_merge_selection",
    "route_blocker_for_selection",
    "target_confirmation_blocker",
]
