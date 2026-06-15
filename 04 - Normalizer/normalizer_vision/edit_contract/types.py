"""Action and surface constants for the Normalizer edit contract."""

DESCRIBE_SURFACES_ACTION = "describe_surfaces"
READ_BUNDLE_ACTION = "read_bundle"
READ_SURFACE_ACTION = "read_surface"
VALIDATE_SURFACE_ACTION = "validate_surface"
WRITE_SURFACE_ACTION = "write_surface"

SETTINGS_SURFACE_ID = "normalizer.settings"
PROMPT_OVERRIDES_SURFACE_ID = "normalizer.prompt_overrides"
PROMPT_BUNDLE_SURFACE_ID = "normalizer.prompt_bundle"
TAXONOMY_MASTER_SURFACE_ID = "normalizer.taxonomy_master"
TAXONOMY_PROFILES_SURFACE_ID = "normalizer.taxonomy_profiles"
TRANSLATION_GLOSSARY_SURFACE_ID = "normalizer.translation_glossary"
SEMANTIC_RELEASE_AUTHORING_SURFACE_ID = "normalizer.semantic_release_authoring"
TAXONOMY_RELEASE_DRAFT_SURFACE_ID = "normalizer.taxonomy_release_draft"
DEBUG_CAPABILITIES_SURFACE_ID = "normalizer.debug_capabilities"

SURFACE_IDS = (
    SETTINGS_SURFACE_ID,
    PROMPT_OVERRIDES_SURFACE_ID,
    PROMPT_BUNDLE_SURFACE_ID,
    TAXONOMY_MASTER_SURFACE_ID,
    TAXONOMY_PROFILES_SURFACE_ID,
    TRANSLATION_GLOSSARY_SURFACE_ID,
    SEMANTIC_RELEASE_AUTHORING_SURFACE_ID,
    TAXONOMY_RELEASE_DRAFT_SURFACE_ID,
    DEBUG_CAPABILITIES_SURFACE_ID,
)

SOURCE_TOOL_ACTIONS = (
    "create_release_package",
    "read_release_package",
    "read_translation_glossary_locale",
    "list_master_terms",
    "read_master_term",
    "upsert_master_term",
    "retire_master_term",
    "list_projections",
    "read_projection",
    "create_projection_draft",
    "upsert_projection",
    "set_locale_text",
    "set_routing_lexicon",
)

SOURCE_OPERATION_ACTIONS = (
    "list_default_blueprints",
    "materialize_custom_taxonomy_artifact",
    "materialize_custom_projection_artifact",
    "apply_taxonomy_update_state",
    "apply_projection_update_state",
    "remove_taxonomy_from_release",
    "remove_projection_from_release",
    "validate_projection_binding",
    "compile_semantic_release_candidate",
    "materialize_semantic_release_candidate",
    "merge_semantic_release_candidates",
    "derive_working_release_from_blueprint",
    "create_minimal_custom_release",
    "preview_impact",
    "review_bootstrap_release",
    "bootstrap_release_package",
    "review_data_informed_release",
    "refine_release_package",
    "validate_release_package",
    "compile_release_package",
    "export_semantic_release",
    "activate_semantic_release",
    "create_and_activate_new_corpus_db",
)

SOURCE_ACTIONS = SOURCE_TOOL_ACTIONS + SOURCE_OPERATION_ACTIONS
