"""Action and surface constants for the orchestrator edit contract."""

from ..policy_store import (
    ARTIFACT_PUBLICATION_SURFACE_ID,
    EXECUTION_SURFACE_ID,
    HEALTH_DEPENDENCY_SURFACE_ID,
    ROUTE_INTAKE_SURFACE_ID,
)

DESCRIBE_SURFACES_ACTION = "describe_surfaces"
READ_BUNDLE_ACTION = "read_bundle"
READ_SURFACE_ACTION = "read_surface"
VALIDATE_SURFACE_ACTION = "validate_surface"
WRITE_SURFACE_ACTION = "write_surface"

SURFACE_IDS = (
    ROUTE_INTAKE_SURFACE_ID,
    EXECUTION_SURFACE_ID,
    HEALTH_DEPENDENCY_SURFACE_ID,
    ARTIFACT_PUBLICATION_SURFACE_ID,
)
