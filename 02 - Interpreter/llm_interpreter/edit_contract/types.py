"""Action and surface constants for the Interpreter edit contract."""

DESCRIBE_SURFACES_ACTION = "describe_surfaces"
READ_BUNDLE_ACTION = "read_bundle"
READ_SURFACE_ACTION = "read_surface"
VALIDATE_SURFACE_ACTION = "validate_surface"
WRITE_SURFACE_ACTION = "write_surface"

RUNTIME_POLICY_ENV_SURFACE_ID = "interpreter.runtime_policy_env"
EXECUTION_LIMITS_SURFACE_ID = "interpreter.execution_limits"
PROMPT_BUNDLE_SURFACE_ID = "interpreter.prompt_bundle"
OUTPUT_CONTRACT_PREVIEW_SURFACE_ID = "interpreter.output_contract_preview"
DEBUG_CAPABILITIES_SURFACE_ID = "interpreter.debug_capabilities"

SURFACE_IDS = (
    RUNTIME_POLICY_ENV_SURFACE_ID,
    EXECUTION_LIMITS_SURFACE_ID,
    PROMPT_BUNDLE_SURFACE_ID,
    OUTPUT_CONTRACT_PREVIEW_SURFACE_ID,
    DEBUG_CAPABILITIES_SURFACE_ID,
)
