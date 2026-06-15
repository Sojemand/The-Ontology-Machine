"""Owner-provided summary text for the Corpus Builder Edit Suite slot."""

from __future__ import annotations

from textwrap import dedent


def build_module_summary() -> str:
    return dedent(
        """
        CORPUS BUILDER HELP

        Purpose
        This slot prepares the Corpus Builder's next saved configuration and module-owned maintenance actions. The module loads `*.structured.normalized.json` bundles into one `corpus.db`, keeps one active semantic release per database, and supports fulltext, semantic, and hybrid retrieval.
        This slot is an authoring and operations shell for owner-local files only. It does not pick source documents for you and it does not start Orchestrator debug sessions by itself.

        How To Read This Slot
        - Summary explains module role, release state, readiness signals, and boundaries.
        - Settings controls storage paths, archive behavior, page-image persistence, semantic state paths, and the semantic maintenance actions.
        - Prompts/Assets stays empty here because the published release bundle is no longer a free-form edit surface.
        - Operations shows contract actions and action buttons that run against saved owner files or explicit exported JSON bundle paths.
        - Preview/Drift is the review layer for current values, draft values, and diffs before save.

        Surface Guide
        - Settings (`corpus_builder.settings`): edits selected groups inside `config/corpus_config.json`. The main groups are Storage, Archive / FTS, and Source / Semantic. This surface also exposes `Semantic Status`, `Stage Release`, `Activate Release`, `Create and Activate New Corpus DB`, `Rebuild Corpus`, `Create New Corpus DB`, `Semantic Audit`, and `Backfill Stale`.
        - Embeddings Policy (`corpus_builder.embeddings_policy`): edits the `embeddings` subtree in `config/corpus_config.json`.
        - Search Policy (`corpus_builder.search_policy`): edits `config/search_policy.json` for fulltext, semantic, and hybrid defaults.
        - Published Release Bundle (`config/semantic_release.default.json`): visible in Summary and used by semantic actions, but not exposed as a direct edit surface.
        - Owner Capabilities: the Summary cards mirror read-only manifest and state facts from `module-manifest.json`, `config/semantic_release.default.json`, `state/semantic_release.active.json`, and `state/semantic_release_report.json`.

        Settings Reference
        - `database.corpus_db`: default database path for corpus operations. This may point into the Orchestrator artifact folder and is switched to a newly created database after the explicit create flow succeeds.
        - `archive.enabled`: enables archive handling for replaced or superseded documents.
        - `archive.keep_archived`: keeps archived records queryable for maintenance and export flows.
        - `fts.enabled`: enables SQLite fulltext indexing for searchable text.
        - `fts.tokenizer`: tokenizer used for the FTS layer.
        - `source.page_images_dir`: optional module-local root for page-image discovery when images should be persisted.
        - `source.persist_page_images_in_db`: stores discovered page images in `document_page_images` during future load or rebuild flows.
        - `semantic.published_release_path`: file path used as the module's published or staged semantic release.
        - `semantic.active_release_path`: file path used for the currently active semantic release copy.
        - `semantic.release_report_path`: file path where release analysis reports are written.
        - Settings changes affect later rebuild, load, semantic, and stats or export actions only after save. They do not rewrite an existing `corpus.db` on their own.

        Embeddings Guide
        - `embeddings.dimensions` must match the vector size expected by the embedding model that will be used at runtime.
        - `embeddings.batch_size` controls how many items are grouped per embedding request.
        - `embeddings.max_text_chars` limits how much source text is sent for one embedding item.
        - These values are preparation settings for the next `Generate Embeddings` run. Existing vectors stay unchanged until a future embedding generation or rebuild writes new data.
        - The embedding model itself is intentionally outside this slot. The Edit Suite can pass a runtime model to an action, but that model choice remains orchestrator-owned rather than saved owner config.

        Search Policy Guide
        - `fulltext.limit_default` is the default result size for fulltext queries.
        - `semantic.top_k_default` is the default candidate count for semantic-only queries.
        - `hybrid.top_k_default` is the default final hit count for hybrid search.
        - `hybrid.candidate_multiplier` controls how many extra candidates are gathered before hybrid reranking.
        - `hybrid.fts_weight` and `hybrid.vec_weight` split the hybrid score and must add up to `1.0`.
        - `readonly.max_rows` caps large read-only result views.
        - `fts.normalize_by_max_score` toggles score normalization inside the FTS layer.
        - Search policy changes affect the next search action only. They do not rebuild indexes or change stored documents.

        Semantic Release Guide
        - `config/semantic_release.default.json` is the module's published JSON release bundle, not an editable authoring surface.
        - `Stage Release` accepts only exported `.json` bundles, validates fingerprint plus schema, copies the bundle to the configured published path, and writes a fresh analysis report.
        - `Activate Release` stages and applies only exported `.json` bundles, then checks file state versus database installation state.
        - `Semantic Status` reads the file-backed active and published release situation and reports pending changes plus installation-state drift.
        - `Semantic Audit` re-analyzes the published release and checks it against the current database situation.
        - `Backfill Stale` rematerializes stale documents against the active release. It assumes that an active release already exists.
        - The published bundle under `config/` and the active and report files under `state/` are operational release files. They may be inspected in Summary, but they are not normal editable surfaces.

        What The Action Buttons Do
        - `Rebuild Preview` scans an artifact cluster and reports what would be rebuilt before any database write happens.
        - `Rebuild Corpus` rebuilds an existing `corpus.db` from artifact folders and can optionally replace that existing database in place.
        - `Create New Corpus DB` opens a confirmation dialog, provisions a fresh DB under the confirmed Corpus root, rebuilds into that new file, and then switches the default DB path without touching the old database.
        - `Generate Embeddings` computes embeddings for the current database using the saved embeddings policy plus a runtime model input.
        - `Search Corpus` runs a fulltext, semantic, or hybrid search against the selected database.
        - `Corpus Stats` loads document and storage statistics for the selected database.
        - `Export Corpus` writes the current corpus to JSONL or CSV.
        - `Semantic Status` loads active, published, and pending semantic state for the selected database.
        - `Stage Release` validates and stages an exported JSON release bundle to the module's published path.
        - `Activate Release` stages and then activates an exported JSON release bundle for an existing selected database.
        - `Create and Activate New Corpus DB` opens a confirmation dialog, provisions a fresh DB under the confirmed Corpus root, activates the release there, and then switches the default DB path without touching the old database.
        - `Semantic Audit` checks the published release, its analysis report, and the database state for drift or compatibility issues.
        - `Backfill Stale` rematerializes stale documents with the active release after a release change.

        What This Slot Does Not Control
        - It does not let you browse input artifacts and load one document directly. That workflow belongs to Orchestrator Debug Host or CLI via `scan_debug_input`, `debug_run`, and `load_document`.
        - It does not replace health diagnostics. `healthcheck` stays a module capability, not a main editing surface.
        - It does not expose free-form editing for `config/semantic_release.default.json`.
        - It does not expose free-form editing for `state/semantic_release.active.json` or `state/semantic_release_report.json`.
        - It does not decide the runtime embedding model that external services use.
        - It does not retroactively mutate stored documents, vectors, or release state until you run a later operation against saved files.

        Recommended First-Time Workflow
        1. Start in Summary so you understand the current database path, release paths, readiness signals, and slot boundaries.
        2. Open Settings and confirm `database.corpus_db`, archive behavior, and whether page images should be persisted in the database.
        3. Open Embeddings Policy and verify the vector dimensions, batch size, and text limit before running any embedding action.
        4. Open Search Policy and check result limits, hybrid weights, and filter behavior so search results match your expectations.
        5. Inspect the published and active bundle state in Summary, then use the Settings action buttons when you want to stage or activate an exported JSON release bundle.
        6. Save owner-file changes first, then use `Semantic Status` or `Stage Release` to verify the semantic file situation before activating anything.
        7. Use `Rebuild Preview` before `Rebuild Corpus` when you are working with a new artifact cluster or are unsure which bundles will be included.
        8. Run `Generate Embeddings`, `Search Corpus`, `Corpus Stats`, or `Export Corpus` only after the saved configuration and release state match your intent.
        """
    ).strip()
