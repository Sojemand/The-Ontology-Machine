"""Debug-help resources for the Corpus Builder module."""

from __future__ import annotations

HELP_ENTRIES = {
    "corpus_builder": (
        "Corpus Builder Debug Guide",
        """OVERVIEW

This help applies only to the Corpus Builder inside the Debug tab.
Use this window when you want to preview or rebuild corpus-load inputs without starting the full pipeline.

WHAT THIS DEBUG WINDOW IS GOOD FOR

- Preview which normalized artifact bundles would be loaded into a fresh session corpus.
- Load one concrete `*.structured.normalized.json` into an isolated debug-session database.
- Rebuild `outputs/corpus.db` from an artifact folder and inspect the written reports.
- Confirm semantic-release compatibility before a larger corpus rebuild.

WHAT THE CONTROLS IN THIS WINDOW DO

- Module: selects the target debug module. Keep it on Corpus Builder for this guide.
- Mode:
  - Scan: preview only, no database write.
  - Single: load exactly one normalized document into a fresh session database.
  - Batch: rebuild one session database from an artifact folder.
- Input Path:
  - Scan and Batch expect an artifact folder, typically with `normalized/` and optionally sibling `structured/`, `validation/`, or `page_images/`.
  - Single expects exactly one `*.structured.normalized.json`.
  - This path goes directly into the Corpus Builder debug run. The main Input Folder from the Status tab is not used here.
- Persist Page Images in DB:
  - overrides page-image persistence for the current debug run only.
  - enabled means the loader tries to persist matching page images into `document_page_images` inside `outputs/corpus.db`.
  - disabled means the debug run skips DB page-image persistence even if matching `page_images/` artifacts exist.

MODE BEHAVIOR IN DEBUG

Scan
- Runs only `corpus_builder:scan_debug_input`.
- Writes `outputs/preview_report.json`.
- Does not create `outputs/corpus.db`.

Single
- Runs `corpus_builder:debug_run` with `mode=single`.
- Loads exactly one `*.structured.normalized.json`.
- Writes a fresh session-local `outputs/corpus.db` plus `outputs/preview_report.json` and `outputs/load_report.json`.

Batch
- Runs `corpus_builder:debug_run` with `mode=batch`.
- Rebuilds `outputs/corpus.db` from the selected artifact folder.
- Uses the active Semantic Release from the Corpus Builder state and aborts the rebuild if the normalized payloads are incompatible with that release.
- Does not run embeddings. The normal orchestrated pipeline runs embeddings automatically after successful corpus loads, but this debug run keeps rebuilds isolated.

SEMANTIC RELEASE

- An active Semantic Release is required for batch rebuilds and for the normal orchestrated pipeline.
- The release defines the active projection and materialization contract that normalized payloads must match before they are written into `corpus.db`.
- If the Orchestrator GUI field is empty, the Corpus Builder still needs an already active release in its own state.
- Runtime-installer builds can currently ship without an active release. In that situation the normal pipeline aborts at start with a Corpus Builder hint until a release is activated.
- Choosing a release in the Orchestrator activates it once for the target `corpus.db` before the main run. This debug window uses the already active release; it does not create embeddings and it does not silently bootstrap a missing release.

WHAT YOU CAN INSPECT HERE

- Artifacts: `outputs/corpus.db`, `outputs/preview_report.json`, `outputs/load_report.json`, and the session files `request.json`, `response.json`, `snapshot.json`, `result.json`, `run.log`.
- Preview tab: pretty-printed JSON or text for the currently selected artifact.
- Replay tab: offline loading of existing corpus debug artifacts, including `corpus.db`.
- Open Artifacts: open the written session tree in Explorer for external inspection.

IMPORTANT NOTES

- Single mode accepts only `*.structured.normalized.json`, not `*.structured.json` and not original PDFs or images.
- Batch rebuilds depend on the active Semantic Release being compatible with the selected normalized payloads.
- This debug run does not create embeddings. It only writes the corpus-load artifacts and optional page-image blobs.
- `corpus.db` is a SQLite binary artifact and is intentionally not rendered inline. Inspect it through Open Artifacts or an external SQLite viewer.
- The session monitor refreshes automatically while the debug session is running.
- Refresh forces an immediate poll. It does not restart the run.
- Cancel writes a cooperative cancel request.""",
    ),
}
