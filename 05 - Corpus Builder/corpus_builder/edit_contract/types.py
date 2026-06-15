"""Action and surface constants for the Corpus Builder edit contract."""

DESCRIBE_SURFACES_ACTION = "describe_surfaces"
READ_BUNDLE_ACTION = "read_bundle"
READ_SURFACE_ACTION = "read_surface"
VALIDATE_SURFACE_ACTION = "validate_surface"
WRITE_SURFACE_ACTION = "write_surface"

SETTINGS_SURFACE_ID = "corpus_builder.settings"
EMBEDDINGS_POLICY_SURFACE_ID = "corpus_builder.embeddings_policy"
SEARCH_POLICY_SURFACE_ID = "corpus_builder.search_policy"
DEBUG_CAPABILITIES_SURFACE_ID = "corpus_builder.debug_capabilities"

SURFACE_IDS = (
    SETTINGS_SURFACE_ID,
    EMBEDDINGS_POLICY_SURFACE_ID,
    SEARCH_POLICY_SURFACE_ID,
)

__all__ = [
    "DEBUG_CAPABILITIES_SURFACE_ID",
    "DESCRIBE_SURFACES_ACTION",
    "READ_BUNDLE_ACTION",
    "EMBEDDINGS_POLICY_SURFACE_ID",
    "READ_SURFACE_ACTION",
    "SEARCH_POLICY_SURFACE_ID",
    "SETTINGS_SURFACE_ID",
    "SURFACE_IDS",
    "VALIDATE_SURFACE_ACTION",
    "WRITE_SURFACE_ACTION",
]
