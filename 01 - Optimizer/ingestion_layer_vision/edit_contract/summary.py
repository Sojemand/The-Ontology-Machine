"""Owner-provided summary text for the Optimizer Edit Suite slot."""

from __future__ import annotations

from textwrap import dedent


def build_module_summary() -> str:
    return dedent(
        """
        OPTIMIZER HELP

        Purpose
        This slot prepares the merged Optimizer module for orchestrated runs.
        The Optimizer exposes one public `optimizer` slot with `vision` and
        `file` profiles. Both profiles emit `optimizer_raw_v2`; the vision
        profile routes scan-heavy inputs through the Orchestrator-owned
        `optimizer_ocr` LLM target and persists prompt-relevant text only as
        `ocr_reference.blocks`.

        How To Read This Slot
        - Summary explains the profile split, the editable owner settings, and
          the read-only contract previews.
        - Settings contains the editable `config/config.yaml` form grouped into
          Processing and Rendering/Layout.
        - Prompts/Assets contains the editable LLM-OCR prompt used by
          `optimizer_ocr`.
        - Operations shows read-only contract actions from `module-manifest.json`.
        - Preview/Drift contains the read-only Output Contract Preview plus
          current, draft, and diff views for editable surfaces.

        Surface Guide
        - Settings (`optimizer.settings`): edits `config/config.yaml` with file
          size limits, block limits, timeout behavior, processing order,
          worker concurrency, and file-profile render/layout settings.
        - LLM-OCR Prompt (`optimizer.ocr_prompt`): edits
          `config/optimizer_ocr_prompt.md`, the reusable OCR extraction prompt.
        - Output Contract Preview (`optimizer.output_contract_preview`):
          read-only view of the raw schema, response-path contract, profile
          selector, and LLM-OCR ownership boundary.
        - Debug Capabilities (`optimizer.debug_capabilities`): mirrors
          read-only contract actions such as `classify_document`,
          `extract_document`, `healthcheck`, `scan_debug_input`, and
          `debug_run`.

        Settings Guide
        - `max_file_size_mb`, `max_blocks_per_file`, and
          `max_cell_text_length` cap input and raw payload size before
          downstream modules see the document.
        - `processing_order`, `plugin_timeout_seconds`, and `parallel_workers`
          control next-run execution order, timeout behavior, and local worker
          concurrency.
        - `render_dpi`, `render_width_px`, `render_height_px`,
          `page_margin_pt`, `default_font_size_pt`, `code_font_size_pt`, and
          `heading_font_size_pt` control file-profile rendering/layout paths.

        Prompt Guide
        - `optimizer.ocr_prompt` is the only Optimizer prompt edited here.
        - The prompt must keep `{page_count}` so runtime can tell the model how
          many rendered images are in the OCR request.
        - `{source_filename}` and `{source_filename_sentence}` are optional
          placeholders resolved at runtime.

        Output Contract Guide
        - Persistent raw files contain `source`, `extraction`, `metadata`,
          `context`, and `ocr_reference.blocks`.
        - Persistent raw files do not contain page asset paths, synthetic
          summaries, sections, facts, tables, runtime traces, or compression
          audits.
        - Extract responses expose `document_raw_path`, `page_raw_paths`, and
          `page_asset_paths`; page assets are response-only working paths and
          are not serialized into persistent raws.

        LLM-OCR Boundary
        - Productive OCR uses the central `optimizer_ocr` port and the
          `OPTIMIZER_OCR_*` process overlay.
        - The prompt is owner-local, but provider, model, token budget, timeout,
          and credentials are
          Orchestrator-owned and are not edited in this slot.
        - Local OCR plugin folders, GPU/CPU OCR selection, and local OCR
          fallback are no longer part of the Optimizer edit surface.

        What This Slot Does Not Control
        - It does not author projection catalogs or semantic extraction policy.
        - It does not choose provider, model, auth, or secret settings for
          `optimizer_ocr`.
        - Existing raw extracts change only after a future module run uses the
          saved owner files.
        """
    ).strip()
