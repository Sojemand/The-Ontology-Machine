"""Status-tab help texts for the orchestrator desktop UI."""

from __future__ import annotations

STATUS_TITLE = "Status Tab Guide"
STATUS_BODY = """OVERVIEW

The Status tab is the main operator surface for end-to-end pipeline runs.
Use it to define the active folders, choose the run mode, start or stop processing, and watch stage progress.

WHAT YOU CONFIGURE HERE

- Input Folder: root folder the pipeline reads from.
- Artifact Folder: target root for published success and error artifacts.
- Database Storage Folder: folder where the Orchestrator keeps selectable corpus database files.
- Selected Database: the concrete `.db` file the next run will target.
- Semantic Release: optional override release file you can activate explicitly for the selected database.
- Semantic Release Mode: choose whether the run uses the selected database's active release or an explicit override release.
- Mode: batch or single for the main pipeline run.

ARTIFACT TREE

- Create Artifact Tree creates the canonical folder tree at the chosen parent/name.
- It sets Input Folder to `<Tree>\\Input`, Artifact Folder to `<Tree>`, Database Storage Folder to `<Tree>\\Corpus`, and Selected Database to `<Tree>\\Corpus\\corpus.db`.
- It leaves the Semantic Release override field untouched; the tree's `Semantic Release` folder is storage, not the UI override picker.

DATABASES

- Create Database creates a new `.db` inside Database Storage Folder.
- When a default release is generated for a new DB, the release JSON is stored in `<Tree>\\Semantic Release` when an Artifact Folder is set.
- New databases can be created either from the canonical default taxonomy with a selected language pack or as an empty database without an active release.
- The selected database is persisted and remains the target database the next time you open the Orchestrator.
- The pipeline always loads into the selected database, not into an implicit `corpus.db` convention.

SEMANTIC RELEASE

- In `DB Release` mode the run resolves runtime semantics from the active snapshot of the selected database.
- In `Override Release` mode the chosen release file becomes an explicit switch target for that database.
- Activate checks the selected override release against the selected database before it applies anything.
- If the selected release is already active or the DB is still uninitialized, Activate goes straight through.
- If the selected release would change the active snapshot for an existing DB, the GUI shows a confirmation dialog with the concrete impact on that DB before activation continues.
- The normal run no longer switches releases silently in the background. If you want to override the DB release, activate it first.
- Corpus Builder must already have an active release for normal runs in `DB Release` mode.
- If the selected database has no active release and you stay in `DB Release` mode, the pipeline aborts at start with a Corpus Builder hint.

RUN CONTROL

- Create Artifact Tree: creates or verifies the canonical tree and bootstraps the related path fields.
- Process: starts the orchestrator pipeline with the current settings.
- Reset Error Bundle: resets only historical error-case data and keeps successful pipeline history.
- Reset Pipeline Logs: removes hidden pipeline history under `state/pipeline/` and clears `state/orchestrator.log` plus backups.
- Abort: requests a controlled stop for the active run.
- Open Edit Suite: starts `06 - Edit Suite\\run.bat` and hands you off to the dedicated config, readiness, drift, and owner-surface shell.
- Help: opens this guide.

WHAT TO EXPECT IN THE EDIT SUITE

- The Edit Suite is the pipeline-wide nerd cockpit for config-adjacent work that should not live in the normal run flow.
- Expect module readiness overviews, drift and contract hints, owner-provided edit surfaces, and non-run operations such as curated release or policy maintenance.
- Use the Orchestrator for productive runs and module debugging. Use the Edit Suite when you want to inspect or maintain what the modules expose for guided editing.

WHAT YOU CAN MONITOR

- Run Status: progress bar and current file / attempt summary.
- Counters: pending, success, errors, review cases, retries.
- Route fields: detected route family, optimizer, interpreter, and intake reason.
- Pipeline Status: per-stage state and detail text across Intake, Runtime Semantics, Optimizer, Request Enrichment, Interpreter, Validator, Normalizer, Corpus Builder, and Embeddings.

WHEN TO USE THE DEBUG TAB INSTEAD

Use the Debug tab when you want to exercise one module in isolation.
Use the Status tab when you want the normal orchestrated end-to-end pipeline flow.

GOOD DEFAULT WORKFLOW

1. Set Input Folder, Artifact Folder, and Database Storage Folder.
2. Select an existing database or create a new one.
3. Leave Semantic Release Mode on `DB Release` for the normal workflow, or switch to `Override Release` if you want to change the selected database deliberately.
4. Pick batch or single main run mode.
5. Start the run and watch the stage cards for progress and failures. Embeddings run automatically after successful corpus loads.
6. Switch to Debug only if you need isolated module investigation."""
