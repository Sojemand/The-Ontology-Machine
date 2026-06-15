from __future__ import annotations

from semantic_control_kernel.workflows.database_creation.route_catalog import (
    DRIFT_PREFLIGHT,
    ROUTE_BY_TOOL,
    ROUTES,
    WORKFLOW_ENTRIES,
)
from semantic_control_kernel.workflows.database_creation.route_steps import STEP_BY_ID, STEP_CATALOG
from semantic_control_kernel.workflows.database_creation.route_types import (
    KERNEL_BOOKKEEPING,
    READ_BUILD_SOURCE_STEP,
    DatabaseCreationRoute,
    DatabaseCreationStep,
)


def get_route(workflow_tool: str) -> DatabaseCreationRoute:
    try:
        return ROUTE_BY_TOOL[workflow_tool]
    except KeyError as exc:
        raise ValueError(f"Unknown Phase 9 database creation workflow: {workflow_tool}") from exc


def get_step(step_id: str) -> DatabaseCreationStep:
    try:
        return STEP_BY_ID[step_id]
    except KeyError as exc:
        raise ValueError(f"Unknown Phase 9 database creation step: {step_id}") from exc


def route_sequence(workflow_tool: str, *, include_optional: bool = False) -> tuple[str, ...]:
    route = get_route(workflow_tool)
    return route.sequence(include_optional=include_optional)


def all_route_sequences() -> dict[str, tuple[str, ...]]:
    return {route.workflow_tool: route.step_ids for route in ROUTES}


__all__ = [
    "DRIFT_PREFLIGHT",
    "KERNEL_BOOKKEEPING",
    "READ_BUILD_SOURCE_STEP",
    "ROUTES",
    "STEP_BY_ID",
    "STEP_CATALOG",
    "WORKFLOW_ENTRIES",
    "DatabaseCreationRoute",
    "DatabaseCreationStep",
    "all_route_sequences",
    "get_route",
    "get_step",
    "route_sequence",
]
