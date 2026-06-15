"""Surface and schema constants for orchestrator policy configs."""

ROUTE_INTAKE_SURFACE_ID = "orchestrator.route_intake_policy"
EXECUTION_SURFACE_ID = "orchestrator.execution_policy"
HEALTH_DEPENDENCY_SURFACE_ID = "orchestrator.health_dependency_policy"
ARTIFACT_PUBLICATION_SURFACE_ID = "orchestrator.artifact_publication_policy"

SURFACE_IDS = (
    ROUTE_INTAKE_SURFACE_ID,
    EXECUTION_SURFACE_ID,
    HEALTH_DEPENDENCY_SURFACE_ID,
    ARTIFACT_PUBLICATION_SURFACE_ID,
)

SURFACE_FILES = {
    ROUTE_INTAKE_SURFACE_ID: "config/route_intake_policy.json",
    EXECUTION_SURFACE_ID: "config/execution_policy.json",
    HEALTH_DEPENDENCY_SURFACE_ID: "config/health_dependency_policy.json",
    ARTIFACT_PUBLICATION_SURFACE_ID: "config/artifact_publication_policy.json",
}

ROUTE_FAMILIES = ("Documents",)
ROUTE_GROUP_KEYS = ("images", "files", "pdf")
MODULE_KEYS = (
    "optimizer",
    "interpreter",
    "validator",
    "normalizer",
    "corpus_builder",
)
PIPELINE_STAGE_NAMES = (
    "Intake",
    "Runtime Semantics",
    "Optimizer",
    "Request Enrichment",
    "Interpreter",
    "Validator",
    "Normalizer",
    "Corpus Builder",
    "Embeddings",
)
OPERATION_NAMES = (
    "extract_document",
    "classify_document",
    "interpret_document",
    "validate_document",
    "normalize_document",
    "load_document",
    "activate_semantic_release",
    "generate_embeddings",
)
ARTIFACT_KEYS = (
    "originals",
    "raw_extracts",
    "page_images",
    "requests",
    "structured",
    "validation",
    "normalized",
    "logs",
)
