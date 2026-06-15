"""Shared config and runtime constants for Normalizer Vision."""
from __future__ import annotations

from pathlib import Path

DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_TIMEOUT_SECONDS = 300
DEFAULT_MAX_OUTPUT_TOKENS = 15_000
DEFAULT_RUNTIME_THINKING_LABEL = "no thinking"
FIXED_API_REASONING_EFFORT = "none"
PROJECTION_HINT_MODE_OPTIONS = ["off", "advisory", "strict"]
DEFAULT_MAX_STRUCTURED_BYTES = 10_000_000
DEFAULT_MAX_BATCH_FILES = 500
DEFAULT_MAX_BATCH_WORKERS = 8
DEFAULT_CONFIG_RELATIVE_PATH = Path("config/config.yaml")
LEGACY_ASSET_KEYS = {
    "prompt_overrides_path": "config/prompt_overrides.json",
}
REMOVED_INTERNAL_PATH_FIELDS = frozenset(
    {
        "taxonomy_master_path",
        "taxonomy_profile_path",
        "prompt_bundle_path",
        "semantic_release_recipe_path",
    }
)
REMOVED_RUNTIME_CONFIG_FIELDS = frozenset({"model", "max_output_tokens", "thinking_effort"})
CONFIG_INT_FIELDS = {
    "timeout_seconds",
    "max_retries",
    "retry_delay_seconds",
    "default_workers",
    "max_structured_bytes",
    "max_batch_files",
    "max_batch_workers",
}
CONFIG_BOOL_FIELDS = {"structured_outputs"}
RUNTIME_SETTINGS_REQUIRED_MESSAGE = (
    "Lokale LLM-Laeufe erfordern orchestrator-injizierte runtime_settings. "
    "Ein Solo-Run ueber einen geladenen Orchestrator ist vorbereitet, aber in diesem Schritt noch nicht implementiert."
)
