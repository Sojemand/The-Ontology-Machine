# Orchestrator

Standalone Windows Orchestrator for The Ontology Machine pipeline.

## Runtime Build

- Target platform: Windows x64.
- Bundled runtime: CPython 3.11 x64.
- Offline source for runtime packages: `runtime/wheelhouse`.
- Runtime contract: `runtime/runtime-manifest.json`.

Build runtime:

```bat
build-runtime.bat
```

Check portable runtime:

```bat
check-runtime.bat
```

## Per-User Installation

- Install target: user-writable folder.
- No administrator rights required.
- No preinstalled Python required.
- No internet required for normal operation.

Build Inno Setup stage or installer:

```bat
build-installer.bat
build-installer.bat --compile
```

Default installer target:

```text
%LOCALAPPDATA%\Programs\Vision Pipeline\00 - Orchestrator
```

The Orchestrator intentionally remains a module slot inside the pipeline root.
Even after installation, sibling modules referenced by `module-registry.json`
are expected relative to the Orchestrator in the same pipeline root.

## Product Role

The Orchestrator is the local desktop control surface for direct pipeline
operation and debugging. It owns:

- GUI state and launcher workflow.
- Pipeline queue, run lifecycle and reset actions.
- Route/intake policy.
- Module registry and sibling-module health checks.
- Runtime credential resolution for pipeline runs.
- Debug Host sessions for sibling-module contract debugging.
- Artifact publication into `Documents/` and `Error Cases/`.

It does not own the internal truth of Optimizer, Interpreter, Validator,
Normalizer or Corpus Builder. Those modules are called through their contracts.

## Edit Contract

- Product contract: `orchestrator.orchestrator_contract`.
- Owner-local headless Edit Suite contract: `orchestrator.edit_contract`.

Call shape:

```bat
python -m orchestrator.edit_contract --request <request.json> --response <response.json>
```

The edit contract describes and edits only four owner-local policy surfaces:

- `orchestrator.route_intake_policy`
- `orchestrator.execution_policy`
- `orchestrator.health_dependency_policy`
- `orchestrator.artifact_publication_policy`

GUI state under `state/ui_state.json`, `state/runtime_settings.json`,
credentials and protocol constants remain outside this edit contract.

The product contract action `activate_corpus_context` may set the
Orchestrator-owned Corpus context. It validates that the target DB exists,
points to a file and stays inside the provided `corpus_output_folder`; it then
sets `selected_corpus_db_path`, `corpus_output_folder`,
`semantic_release_mode=database_default` and clears `semantic_release_path`.

## Development

Local dev tests with the same major runtime version as the bundled runtime:

```bat
dev-tests\bootstrap.bat
dev-tests\run-tests.bat
```

From the repository root:

```bat
run-dev-tests.bat --module "00 - Orchestrator"
```

## Main Architecture And Debugging

`orchestrator.main` is the path-stable package surface for module startup.

Main stages:

- `surface`: argument parsing and minimal entrypoint dispatch.
- `workflow`: logging setup, startup prerequisites and GUI startup.

Compatible entrypoints:

- `python -m orchestrator`
- `run.bat`
- `from orchestrator import main`

Debug routing:

- Startup arguments: inspect `surface`.
- Runtime or GUI startup issues: inspect `workflow`.

## Runtime Model

- The GUI works with exactly one `Artifact Folder`.
- GUI settings are persisted debounce-style into `state/ui_state.json` without
  a separate save step and are flushed at focus-out, tab change, run start and
  app close.
- Non-GUI policy defaults live owner-locally under `config/*.json`.
- Persistent success artifacts are written route-locally under the Artifact
  Folder:
  - `Documents/originals/`
  - `Documents/raw_extracts/`
  - `Documents/page_images/`
  - `Documents/requests/`
  - `Documents/structured/`
  - `Documents/validation/`
  - `Documents/normalized/`
  - `Documents/logs/`
- Terminal failures, review cases and aborts are frozen under:
  - `Error Cases/<ModuleName>/<RouteName>/...`
- Document-scoped working artifacts are created during active runs under:
  - `state/pipeline/runs/<run_id>/d.<hash>/...`

There is no separate global Error Folder and no separate review collection path.

Successful documents move their original into `Documents/originals/...` only at
the end and publish raw extracts, page images, requests, structured,
validation, normalized and per-document run logs at that point.

Final error/review/abort cases move the original canonically into
`Error Cases/<ModuleName>/<RouteName>/originals/...` and must not leave
document-related artifacts in `Documents` after completion.

## Reset Actions

`Reset Error Bundle`:

- Clears `Error Cases` plus a possible legacy `errors/` tree.
- Moves archived originals back into the Input folder where possible.
- Leaves `corpus.db`, success artifacts and successful state records unchanged.

`Reset Pipeline Logs`:

- Clears hidden run history under `state/pipeline/`.
- Clears `state/orchestrator.log`, backups and legacy
  `vision_orchestrator.log*`.
- Does not touch artifacts, `corpus.db`, `debug_sessions/`, credentials or
  settings.

## Pipeline Stages

Logical stages:

- Intake
- Optimizer
- Request Enrichment
- Interpreter
- Validator
- Normalizer
- Corpus Builder
- Embeddings

Live federation modules:

- `optimizer`
- `interpreter`
- `validator`
- `normalizer`
- `corpus_builder`

Supported document route family:

- `Documents`

Supported extensions include common image formats, mail formats, Office/text
formats and PDFs.

PDF routing:

- Born-digital PDF -> `optimizer_profile=file`, `interpreter_profile=file`.
- Scan PDF -> `optimizer_profile=vision`, `interpreter_profile=vision`.

Preflight runs in two phases:

1. Discovery plus intake classification.
2. Healthcheck only for live modules required by the actual ready queue.

For `vision`, Optimizer OCR is required as an LLM OCR dependency. For `file`,
route-specific required dependencies are scoped from the ready queue.

## Runtime Layout

| Path | Role | Mutable |
| --- | --- | --- |
| `orchestrator/` | Product code and package surfaces | no |
| `config/` | Owner-local policy defaults for Edit Suite and runtime | yes |
| `runtime/python` | Bundled CPython runtime | no |
| `runtime/runtime-manifest.json` | Packaging and runtime provenance contract | no |
| `runtime/wheelhouse` | Offline runtime rebuild source | no after build |
| `state/` | Local UI, credential and GUI log state | yes |
| `state/pipeline/` | `pipeline_state.json` plus transient active-run files | yes |
| `<Artifact Folder>/Documents|Error Cases` | Persistent product artifacts | yes |

`check-runtime.bat` validates only the local bundle and provenance contract.
Sibling-module federation is checked separately at startup against
`module-registry.json`.

## Semantic Release

- The GUI may point to an explicit `Semantic Release` file.
- Before a run, the Orchestrator activates that release once for the target
  `corpus.db`.
- Without an explicit release file, the Orchestrator uses the already active
  release state known by Corpus Builder.

## Credentials Resolver

`orchestrator.credentials` is the path-stable surface for central
Orchestrator authentication ownership.

Important state files:

- `state/credentials_state.json`: non-sensitive credential metadata and
  presence flags.
- `state/model_catalog_state.json`: non-sensitive model catalog cache.
- `state/keystore.enc` plus lock: DPAPI-protected API keys.
- `state/oauth_token.enc` plus lock: DPAPI-protected OAuth session.
- `state/oauth_latest_report.json`: sanitized OAuth report without token
  values.

Credential targets:

- `llm_shared`: shared LLM credential for Interpreter and Normalizer.
- `optimizer_ocr`: separate LLM credential for Optimizer OCR.
- `embeddings`: separate credential for Corpus Builder embeddings.
- `oauth`: browser/PKCE login with DPAPI cache and sanitized metadata.

The Orchestrator remains the only auth owner. Sibling modules receive ephemeral
runtime credentials through subprocess environment overlays, never through
request JSON.

Current LLM resolver semantics:

- Active OpenAI OAuth session -> Interpreter, Normalizer and OpenAI
  Optimizer OCR may run through OAuth.
- Otherwise Interpreter and Normalizer use `llm_shared`.
- `optimizer_ocr` uses its own credential target.
- Embeddings stay logically separate; missing embedding credentials do not
  block OAuth pipeline paths, but embeddings are skipped with a visible warning.

## UI Architecture And Debugging

`orchestrator.ui` is the path-stable desktop GUI surface. External import:

```python
from orchestrator.ui import OrchestratorApp
```

UI stages:

- `surface`: thin `OrchestratorApp` entry and dispatch layer.
- `repository`: `UiState` mapping and persistence.
- `validation`: hard startup invariants.
- `workflow`: worker start, abort, queue drain, finish and cleanup.
- `debug_*`: generic Debug tab and session persistence.
- `layout`, `credentials_layout`, `rendering`, `credentials_rendering`,
  `dialogs`: Tk boundaries for visible UI.
- `policy`: view-model formatting for status, colors and details.

The startup path builds only shell plus `Status` immediately. `Debug`,
`Credentials`, `Models` and `Log` are built lazily on first tab switch.

## Models And State

- `orchestrator.models` is the path-stable surface for shared Orchestrator
  types.
- `orchestrator.model_catalog` owns the non-sensitive model catalog cache and
  provider-verified refreshes.
- `orchestrator.state` owns UI and pipeline state persistence.
- `orchestrator.credentials.repository` separately owns non-sensitive
  credential resolver state.

State layers:

- `surface`: stable load/save API and `atomic_json_write`.
- `repository`: `UiState` and `PipelineState` serialization.
- `adapter`: raw JSON file I/O and atomic writes.

## Worker And Integration Boundaries

- `orchestrator.worker` owns worker start and process abort.
- `orchestrator.integrations` owns sibling-module dispatch, healthcheck
  orchestration and contract parsing.
- Subprocess and response-file boundaries are kept inside integration adapters.
- Contract failure text, result parsing and health coercion are kept separate
  from stage dispatch.

## Pipeline Architecture

`orchestrator.pipeline` exposes `OrchestratorEngine`,
`OrchestratorBusyError` and `OrchestratorCancelled`.

Main cuts:

- `surface`: engine construction and public methods.
- `workflow`: run loop, queue build and reset orchestration.
- `document_workflow`: per-record status setup and linear stage order.
- `optimizer_workflow`, `interpreter_workflow`, `validator_workflow`,
  `normalizer_workflow`, `corpus_workflow`: document stages.
- `repository`: state, artifact and error-bundle mutation.
- `validation`: hard UI/path/file invariants.
- `policy`: output naming, review parsing and conflict suffixes.
- `debug`: snapshot, stage and run-log control.

Visible per-document flow:

```text
Input discovery -> Intake -> Optimizer -> Request Enrichment -> Interpreter -> Validator -> Normalizer -> Corpus Builder -> Embeddings -> Success or Error Case routing
```

After Optimizer, multipage sources are expanded into page-scoped work items.
Each page flows independently through Request Enrichment, Interpreter,
Validator, Normalizer and Corpus Builder. The `DocumentRecord` remains the
aggregate for original file, publication, review state and final disposition.

Retries after Optimizer are page-local. Exhausted single pages are frozen as
diagnostic Error Case artifacts without moving the original; full document
publication waits until all pages are terminal.

## Bootstrap Architecture

`orchestrator.bootstrap` owns registry, manifest and startup checks.

Stages:

- `surface`: stable bootstrap API and constants.
- `adapter`: registry/manifest I/O, module-path resolution, Python candidates
  and runtime dependency imports.
- `runtime_report`: shared runtime/startup health report.
- `validation`: hard manifest/runtime/actions/dependency invariants.
- `workflow`: registry load, runtime spec build and startup prerequisites.
- `types`: named bootstrap specs.

## Contract Actions

`module-manifest.json` points to `orchestrator.orchestrator_contract`.

Supported product actions:

- `run`
- `reset`
- `reset_pipeline_logs`
- `embeddings`
- `activate_corpus_context`
- `inspect_source_document_sample`
- `kernel_llm_runtime_profile`
- `kernel_llm_generate`
- `healthcheck`
- `create_artifact_tree`
- `validate_artifact_tree`
- `create_pipeline_batch_manifest`
- `finalize_pipeline_batch_manifest`

`orchestrator.admin_contract` is the owner-clear headless admin surface for
runtime settings, credential metadata/API-key management and explicit secret
reveal.

Admin actions:

- `inspect_runtime`
- `manage_runtime_settings`
- `manage_credentials`
- `reveal_secret`

`reveal_secret` returns plaintext only with the explicit unlock phrase
`REVEAL_SECRET:<target>` and writes an audit event to `state/admin_audit.jsonl`.

## Installer And Packaging

- `build-installer.bat` uses the module-local `installer/installer-manifest.json`.
- The stage ships default policy files under `config/`.
- The Inno installer treats `config/` like `state/` as persisted user data:
  existing user-edited `config/*.json` files are not overwritten on reinstall.
- The generated `dist/stage/release-manifest.json` declares mutable folders and
  signing targets.
- This module installer intentionally does not ship the complete pipeline
  bundle. It installs only the Orchestrator module slot; sibling modules must
  exist in the same pipeline root.

## Regression Layer

`dev-tests/fixtures/regression/` contains a small replay-based regression layer
with curated end-to-end cases. Regression tests run offline: the Orchestrator is
executed for real, but stage artifacts come from versioned replay files instead
of live module calls.

Representative cases:

- `happy_path`: one-document success run to `corpus.db`.
- `receipt_live`: live capture of a synthetic receipt with real sibling
  modules, frozen as replay.
- `validator_fail`: repeated Validator failure with final Error Case snapshot.
- `interpreter_review`: synthetic Interpreter review path after three attempts.
- `normalizer_review`: synthetic Normalizer review path with final
  `needs_review` success and normalized artifact.

Run:

```bat
python -m pytest dev-tests\tests\test_pipeline_regression.py
```

## Phase 19 Owner Contracts

- `orchestrator/workspace_domain/` owns the Kernel Artifact Tree contract.
- Public owner actions:
  - `create_artifact_tree`
  - `validate_artifact_tree`
- `orchestrator/pipeline_batches/` owns traceable batch identity and
  finalization.
- Public owner actions:
  - `create_pipeline_batch_manifest`
  - `finalize_pipeline_batch_manifest`
- Canonical manifest location:

```text
<artifact_root>/Documents/logs/pipeline_batches/<pipeline_batch_id>/pipeline_batch_manifest.json
```

Kernel owner-run evidence correlates materialized DB rows from active
`documents` entries by exact materialized hash when available, otherwise by the
governed source file name from Input/original refs. This keeps scan PDFs and
page-wise documents valid when Corpus Builder stores per-page/content hashes
instead of the original file byte hash.

## Deviation Log

The Orchestrator remains a special case in the federation: it has a desktop GUI
and owns pipeline control, while sibling modules are headless processing slots.
That is intentional. Action names such as `run`, `reset`, `embeddings` and
`healthcheck` remain stable because UI, worker and subprocess dispatch share
the same public action literals.
