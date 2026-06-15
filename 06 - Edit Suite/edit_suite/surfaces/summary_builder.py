"""Summary-body builders for generic and owner-provided module bundles."""
from __future__ import annotations

from ..registry.types import ModuleReadinessEntry
from .types import ModuleSurfaceBundle


def summary_body(entry: ModuleReadinessEntry, bundle: ModuleSurfaceBundle) -> str:
    if bundle.module_summary:
        return bundle.module_summary
    if _is_optimizer(entry):
        return _optimizer_summary_body(entry, bundle)
    labels = ", ".join(surface.label for surface in bundle.surfaces) or "none"
    lines = [f"Slot: {entry.slot_name}", f"Display: {entry.display_name}", f"Readiness: {entry.readiness}", f"Surfaces: {labels}"]
    if entry.diagnostic:
        lines.append(f"Diagnostic: {entry.diagnostic}")
    return "\n".join(lines)


def _is_optimizer(entry: ModuleReadinessEntry) -> bool:
    candidates = (entry.module_key, entry.slot_name, entry.display_name)
    normalized = {str(value or "").strip().casefold().replace("_", " ") for value in candidates}
    return "optimizer" in normalized or "01 - optimizer" in normalized or "optimizer" == str(entry.module_key or "")


def _optimizer_summary_body(entry: ModuleReadinessEntry, bundle: ModuleSurfaceBundle) -> str:
    available = {surface.surface_id for surface in bundle.surfaces}
    lines = [
        "OPTIMIZER HELP",
        "",
        "Purpose",
        "This slot configures and inspects the merged Optimizer module for both vision and file profiles.",
        "The module turns input documents into `optimizer_raw_v2` payloads for downstream Interpreter, Validator, and Normalizer steps.",
        "Vision OCR now runs through the Orchestrator-owned `optimizer_ocr` LLM target. This slot does not edit provider, model, auth, or secrets.",
        "It changes what the next module run will do. It does not launch processing by itself.",
        "",
        "What This Slot Controls",
        "- Settings: runtime limits, ordering, timeout behavior, worker parallelism, and file-profile render/layout values from config/config.yaml.",
        "- LLM-OCR Prompt: the editable `config/optimizer_ocr_prompt.md` prompt used by `optimizer_ocr`.",
        "- Output Contract Preview: read-only raw schema, response-path, page-asset, and LLM-OCR ownership boundaries.",
        "- Operations: a read-only capability view of the module contract and debug hooks.",
        "- Preview/Drift: a comparison view that shows current values, draft values, and diffs before you save.",
        "",
        "What This Slot Does Not Control",
        "- processed_hashes.json is runtime state and is intentionally not edited here.",
        "- This slot does not choose input folders or start extraction runs.",
        "- This slot does not author projection catalogs, semantic extraction policy, local rulesets, provider settings, model settings, or secrets.",
        "",
        "How To Read This Slot",
        "- Readiness tells you whether the module runtime and owner contract loaded correctly.",
        "- Changes in Settings affect the next run, not the current one.",
        "- Changes in LLM-OCR Prompt affect the next OCR call made by `optimizer_ocr`.",
        "- Output Contract Preview is the safe read-only view for checking `optimizer_raw_v2`, `optimizer_profile`, and `optimizer_ocr` boundaries.",
        "- Preview/Drift is the safe review layer. If you see differences there, those edits are still draft changes until you save.",
        "- Operations is informational. It helps you understand what the module exposes, but it is not the main place for day-to-day tuning.",
        "",
        "Settings Reference",
        "- max_file_size_mb: maximum accepted input size in MB. Larger files are rejected before normal processing.",
        "- max_blocks_per_file: upper limit for extracted structural blocks. Use this to cap extreme documents and protect downstream payload size.",
        "- max_cell_text_length: maximum stored text length per extracted cell or value. Lower values trim noisy table content earlier.",
        "- processing_order: input, format, size_asc, or size_desc. This changes the order in which queued files are processed.",
        "- plugin_timeout_seconds: hard timeout for extractor and plugin work. Lower values fail faster; higher values allow slower extraction steps.",
        "- parallel_workers: number of worker threads used for processing. Higher values increase throughput but also raise concurrency and resource use.",
        "- render_dpi, render_width_px, render_height_px, page_margin_pt, default_font_size_pt, code_font_size_pt, and heading_font_size_pt control file-profile rendering/layout behavior.",
        "",
        "Prompt Reference",
        "- LLM-OCR Prompt is the reusable OCR extraction instruction for rendered page/image assets.",
        "- Keep `{page_count}` in the prompt so runtime can inject the request page count.",
        "- `{source_filename}` and `{source_filename_sentence}` are optional runtime placeholders.",
        "",
        "Output Contract Reference",
        "- Persistent raw files keep `schema_version`, `optimizer_profile`, `source`, `extraction`, `metadata`, `context`, and `ocr_reference.blocks`.",
        "- Extract responses keep `document_raw_path`, `page_raw_paths`, and `page_asset_paths`.",
        "- Page assets are response-only working paths for the next Interpreter run and are not serialized into persistent raws.",
        "- LLM-OCR configuration enters only through the `OPTIMIZER_OCR_*` process overlay owned by the Orchestrator.",
        "",
        "Slot Function Notes",
        "- Settings affect size limits, plugin timeout behavior, worker concurrency, and processing order.",
        "- Output Contract Preview helps confirm the raw and response-path contract without editing code-owned behavior.",
        "- The Optimizer no longer exposes local OCR plugin selection, GPU/CPU OCR selection, or local OCR fallback as editable surfaces.",
        "- Operations helps you inspect available contract actions such as classify_document, extract_document, healthcheck, scan_debug_input, and debug_run.",
        "- Preview/Drift helps confirm that the pending draft matches the next-run behavior you intend.",
        "",
        "Pipeline Impact",
        "- Settings change processing limits and execution behavior before raw output is built.",
        "- LLM-OCR still normalizes into the existing OCR-result payload and preserves the downstream `optimizer_raw_v2` contract.",
        "- Because this module sits early in the pipeline, changes here can alter what later Interpreter, Validator, and Normalizer steps receive.",
        "",
        "Recommended Workflow",
        "1. Review Settings first when the issue is about limits, rendering, layout, ordering, timeout, or worker count.",
        "2. Open LLM-OCR Prompt when the issue is about text extraction instructions for rendered page assets.",
        "3. Open Output Contract Preview when the issue is about raw schema, response paths, page assets, or LLM-OCR ownership.",
        "4. Open Preview/Drift and confirm the diff is intentional.",
        "5. Save once the draft matches the behavior you want for the next run.",
    ]
    if "optimizer.settings" not in available:
        lines.append("6. If a surface is missing or broken, fix the contract/runtime problem before treating the module as ready for editing.")
        lines.append("")
        lines.append("Current Limitation")
        lines.append("- Settings is currently unavailable, so this slot cannot fully control runtime behavior.")
    if "optimizer.ocr_prompt" not in available:
        if "Current Limitation" not in lines:
            lines.extend(["", "Current Limitation"])
        lines.append("- LLM-OCR Prompt is unavailable, so OCR prompt authoring is not visible here.")
    if "optimizer.output_contract_preview" not in available:
        if "Current Limitation" not in lines:
            lines.extend(["", "Current Limitation"])
        lines.append("- Output Contract Preview is unavailable, so raw/response-path and LLM-OCR boundaries are not visible here.")
    if "optimizer.debug_capabilities" not in available:
        if "Current Limitation" not in lines:
            lines.extend(["", "Current Limitation"])
        lines.append("- Operations is unavailable, so the module's exposed debug and contract capabilities are not visible here.")
    lines.extend(["", f"Current Status: Readiness = {entry.readiness}."])
    if entry.diagnostic:
        lines.append(f"Diagnostic: {entry.diagnostic}")
    return "\n".join(lines)
