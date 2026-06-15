# 05 - Corpus Builder

`05 - Corpus Builder` is the `corpus_module` for normalized-first loads into a
single SQLite `corpus.db` with FTS, optional embeddings and exactly one active
Semantic Release per database.

## Purpose

- Loads explicit `*.structured.normalized.json` bundles into `corpus.db`.
- Treats normalized JSON as the canonical semantic input.
- Optionally accepts `structured.json` plus Validator report as an evidence
  pair.
- Persists projection, materialization and search data in the same database.
- Stores page images additively in `corpus.db` as evidence backlinks while the
  Artifact Tree page-image folder remains the rebuild surface.

## Public Entry Points

- Headless CLI: `runtime\python\python.exe -m corpus_builder`.
- Contract: `corpus_builder.orchestrator_contract`.
- Actions: see `module-manifest.json` for the canonical list, including
  `merge_preflight` and `merge_corpus_databases`.
- Services: `corpus_builder.services`.

Existing product actions remain stable. The Edit Suite uses additive JSON-ready
owner actions for semantics, search, export and artifact rebuild. Semantic
staging and activation accept only exported `.json` release bundles.

`load_semantic_release` can run with `write_global_mirrors=false` as a
target-scoped Kernel attach check. In this mode the release bundle is read,
validated and evaluated against the given `corpus.db` without changing
module-global mirrors such as `config/semantic_release.default.json`,
`state/semantic_release.active.json` or `state/semantic_release_report.json`.

`rebuild_from_artifacts` can also receive an explicit `release_path` for
Kernel rebuilds. The rebuild validates artifacts against that bundle and does
not write module-global Semantic Release mirrors. The response includes target
proof for Corpus DB, Artifact Root and release fingerprint.

`semantic_status` and `read_active_semantic_release` read target-scoped
databases read-only and do not change journal mode. WAL-mode databases without
writable sidecars fall back to immutable SQLite reads. Mutating flows such as
reset, load or rebuild still use normal write connections.

## Corpus Context Contract

The Corpus Builder owns a product surface for its default database context:

- `activate_corpus_context`
  - Sets `database.corpus_db` in `config/corpus_config.json`.
  - Accepts only an existing file.
  - Reads Semantic status snapshot-first for the same DB.
- `create_empty_corpus_db`
  - Creates an empty SQLite file without active release.
  - Can set the Corpus Builder default when `activate_context=true`.
  - Does not write Orchestrator UI state.
- `create_and_activate_new_corpus_db` /
  `create_and_rebuild_new_corpus_db`
  - Require a confirmation artifact with an explicit `corpus_root`.
  - Do not derive the target folder from Orchestrator UI state.
  - Update `database.corpus_db` only after successful owner mutation.
- `reset_active_corpus_db`
  - Resets the active initialized `corpus.db` to an empty content state after
    confirmed reset evidence.
  - Clears document, materialization, search, evidence, promotion, embedding
    and FTS content tables transactionally.
  - Preserves `installation_state`, `semantic_snapshots`, schema, views and the
    active Semantic Release relation.
  - Compacts SQLite after commit and removes empty idle WAL sidecars
    best-effort after the DB handle is closed.
  - Writes no Orchestrator UI state and no release mirrors.

Shared pipeline context exists only after the Orchestrator also executes its
own `activate_corpus_context` action. Corpus Builder owns `database.corpus_db`;
Orchestrator owns `selected_corpus_db_path`.

## Loader Contract

- Product path: `adapter -> validation -> workflow -> preparation/document_record`.
- `load_document` accepts only `structured_path`, `validation_path`,
  `normalized_path`, `corpus_db_path` plus optional blob/page-image persistence
  parameters.
- `load_from_file` keeps the explicit `validation_path` contract.
- `file_path`, `asset_path` and `source_file_path` semantics are not
  reinterpreted; no hidden contract fields were added.

## Page Image Contract

Page images are stored in `document_page_images` without forcing normal
document, FTS, embedding or list queries to read blobs.

- Switch: `source.persist_page_images_in_db`.
- Default: `true`.
- Images land only in `document_page_images`.
- `documents` remains blob-free.
- `document_payloads.original_blob` is a cold original-file payload and remains
  empty by default.
- `CORPUS_SCHEMA_VERSION` is `7`.

Table contract:

- `document_id TEXT NOT NULL`
- `page INTEGER NOT NULL`
- `content_type TEXT NOT NULL`
- `byte_size INTEGER NOT NULL`
- `image_sha256 TEXT`
- `image_blob BLOB NOT NULL`
- `PRIMARY KEY (document_id, page)`
- `FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE`

## Image Sources And Priority

When `source.persist_page_images_in_db=true`, image lookup uses:

1. explicit `source.page_images_dir`
2. sibling `page_images/` next to the artifact folder `normalized/`

Within one root the resolver tries:

1. exact `file_path` if it already points under `page_images/`
2. `<file_name>.<hash8>` according to Orchestrator convention, including cases
   where the published image folder carries an Optimizer asset hash instead of
   the documented `content_hash`
3. sanitized variant with `_` instead of spaces

Missing or partial images are fail-soft: the document load remains successful,
image rows stay empty or partial, and the loader logs a warning. SQL or
foreign-key errors in the image repository remain fail-fast and roll back the
document transaction.

Page-scoped documents with `source_page` persist only the image for that one
source page. Full-document artifacts without `source_page` may persist all
recognized page images up to `page_count`.

## Config

`config/corpus_config.json`:

```json
{
  "database": {
    "corpus_db": "./output/corpus.db"
  },
  "source": {
    "page_images_dir": "",
    "persist_page_images_in_db": true,
    "persist_original_artifact_in_db": false,
    "max_original_artifact_bytes": 52428800,
    "max_page_image_bytes": 10485760,
    "max_page_image_total_bytes": 104857600
  }
}
```

`page_images_dir` is a root hint for persistable page images. Artifact-based
rebuilds may instead use the sibling `page_images/` folder next to
`normalized/`.

Original files are stored as `document_payloads.original_blob` only when
`persist_original_artifact_in_db=true` and the file size limit allows it.

## Search And Viewer

- FTS, semantic and hybrid search do not read image blobs.
- The Frontend viewer can serve `document_page_images` directly.
- Metadata such as `MAX(page)` remains blob-free.
- Corpora without `document_page_images` remain usable through filesystem
  fallback.

## Runtime

```bat
check-runtime.bat
runtime\python\python.exe -m corpus_builder load --input "<doc>.structured.normalized.json" --corpus-db ".\output\corpus.db"
runtime\python\python.exe -m corpus_builder rebuild --pipeline-root "<pipeline-root>" --corpus-db ".\output\corpus.db"
runtime\python\python.exe -m corpus_builder search --query "final invoice" --corpus-db ".\output\corpus.db"
runtime\python\python.exe -m corpus_builder export --format jsonl --output ".\output\corpus_export.jsonl" --corpus-db ".\output\corpus.db"
```

Additional operation, build, runtime and installer notes live in
`README.operations.md`.

## Edit Suite And Debug Host

The local module GUI was removed. The work-centered UX for:

- Semantics
- Search
- Statistics
- Export
- Artifact rebuild

lives in the generic `06 - Edit Suite` slot.

The generic Orchestrator Debug Host remains responsible for:

- artifact scan through `scan_debug_input`
- single-load into a fresh session DB through `debug_run` with `mode=single`
- batch rebuild into `outputs/corpus.db` through `debug_run` with `mode=batch`
- visible host outputs `outputs/corpus.db`, `outputs/preview_report.json` and
  `outputs/load_report.json`
- owner-local edit contract `corpus_builder.edit_contract`
- additive fast-path action `read_bundle` for the Edit Suite
- visible edit surfaces `corpus_builder.settings`,
  `corpus_builder.embeddings_policy`, `corpus_builder.search_policy`

`config/semantic_release.default.json` remains the published bundle file for
stage/activate, but it is not a free edit surface.

## Test Status

- Module-local `dev-tests`: green at release time.
- Regressions cover tables, loader lifecycle and blob-free search.
- Frontend viewer tests confirm the downstream `document_page_images` contract.
- Direct `pytest` from the module root is bounded by the module-root
  `pytest.ini` to `dev-tests/tests` and excludes generated runtime, dist,
  state and pytest temp artifact trees.

## Phase 19 Owner Contracts

- `corpus_builder/database_analysis/` exposes the read-only owner action
  `read_database_analysis_evidence`.
- The action builds the evidence package for `kernel.analyze_database.input.v1`
  and returns summary, coverage, release-materialization refs,
  affected-document evidence and optional query-manifest payload without
  mutating Corpus state.
- It fails closed when the targeted database is missing or empty, when release
  materialization refs are absent, or when database/release target identity
  drifts.

- `corpus_builder/pipeline_batches/` owns batch inspection, sample extraction,
  original restore, cleanup mutation/journaling and reingest handoff.
- Public owner actions:
  - `inspect_latest_pipeline_batch`
  - `extract_sample_files_for_reingest`
  - `restore_pipeline_batch_originals`
  - `cleanup_pipeline_batch_materialization`
  - `reingest_pipeline_batch`
- Cleanup accepts batch- or selection-scoped cleanup inputs, validates
  destructive confirmation and target identity, deletes only scoped Corpus DB
  records plus derived artifact files, preserves originals/logs/Input/Semantic
  Release files and writes a cleanup journal with post-mutation counts.

- `corpus_builder/semantic_release/` exposes canonical multi-source merge owner
  actions:
  - `multi_source_merge_preflight`
  - `multi_source_merge_databases`
  - `write_merge_reconciliation_manifest`
  - `backfill_sql_from_merge_artifacts`
- The older pairwise `merge_preflight` and `merge_corpus_databases` remain
  legacy helpers only; Phase 19 Kernel happy paths are expected to use the
  `multi_source_merge_*` owner names.
- Filled multi-source merge derives ID maps from actual source SQLite rows,
  copies source document artifacts plus mergeable source-tree file artifacts
  into the target Artifact Tree, writes the combined target database and lets
  `backfill_sql_from_merge_artifacts` verify/update target SQL rows from the
  merge ID map.
