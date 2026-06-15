"""Action and surface constants for the merged Optimizer edit contract."""

DESCRIBE_SURFACES_ACTION = "describe_surfaces"
READ_BUNDLE_ACTION = "read_bundle"
READ_SURFACE_ACTION = "read_surface"
VALIDATE_SURFACE_ACTION = "validate_surface"
WRITE_SURFACE_ACTION = "write_surface"

SETTINGS_SURFACE_ID = "optimizer.settings"
OCR_PROMPT_SURFACE_ID = "optimizer.ocr_prompt"
OUTPUT_CONTRACT_PREVIEW_SURFACE_ID = "optimizer.output_contract_preview"
DEBUG_CAPABILITIES_SURFACE_ID = "optimizer.debug_capabilities"

SETTINGS_FIELD_GROUPS = (
    ("Processing", ("max_file_size_mb", "max_blocks_per_file", "max_cell_text_length", "processing_order", "plugin_timeout_seconds", "parallel_workers")),
    ("Rendering/Layout", ("render_dpi", "render_width_px", "render_height_px", "page_margin_pt", "default_font_size_pt", "code_font_size_pt", "heading_font_size_pt")),
)

SURFACE_IDS = (
    SETTINGS_SURFACE_ID,
    OCR_PROMPT_SURFACE_ID,
    OUTPUT_CONTRACT_PREVIEW_SURFACE_ID,
    DEBUG_CAPABILITIES_SURFACE_ID,
)


def field_groups(groups: tuple[tuple[str, tuple[str, ...]], ...]) -> list[dict[str, object]]:
    return [{"label": label, "fields": list(fields)} for label, fields in groups]

__all__ = [
    "DEBUG_CAPABILITIES_SURFACE_ID",
    "DESCRIBE_SURFACES_ACTION",
    "OCR_PROMPT_SURFACE_ID",
    "OUTPUT_CONTRACT_PREVIEW_SURFACE_ID",
    "READ_BUNDLE_ACTION",
    "READ_SURFACE_ACTION",
    "SETTINGS_FIELD_GROUPS",
    "SETTINGS_SURFACE_ID",
    "SURFACE_IDS",
    "VALIDATE_SURFACE_ACTION",
    "WRITE_SURFACE_ACTION",
    "field_groups",
]
