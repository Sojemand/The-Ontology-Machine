"""Shared policy constants for the Edit Suite."""

from __future__ import annotations

SECTION_ORDER = (
    ("Summary", "Summary"),
    ("Settings", "Settings"),
    ("Prompts/Assets", "Prompts/Assets"),
    ("Operations", "Operations"),
    ("Preview/Drift", "Preview/Drift"),
)

DISCOVERY_CACHE_NAME = "registry_cache.json"
UI_STATE_NAME = "ui_state.json"
BUNDLE_CACHE_DIR_NAME = "bundles"
CONTRACT_TEMP_PREFIX = "edit-contract-"
CONTRACT_TEMP_MAX_AGE_SECONDS = 24 * 60 * 60
OWNER_CONTRACT_TIMEOUT_SECONDS = 30 * 60
