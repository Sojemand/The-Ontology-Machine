# Client Frontend

Local browser frontend for The Ontology Machine. It contains the chat UI,
configuration UI, provider I/O, local persistence, runtime/installer logic and
the read-only minimal database agent used by the Query and Ontology Agents.

## Target Shape

- Canonical product source lives under `client_frontend/`.
- `Client Frontend` is intentionally a manifest-free frontend surface. It is
  not an Orchestrator action module and has no `module-manifest.json`, because
  that would require fake actions or artificial `contract_module` semantics.
- `src/` remains the path-stable build and browser surface.
- `server/` remains the path-stable runtime and direct-run surface.
- `shared/provider-catalog.json` stays root-near and immutable on purpose; it
  is shared contract data for browser and server code.
- Mutable runtime data lives outside the module root under
  `%LOCALAPPDATA%\Enterprise Stack\Client Frontend` or
  `VISION_PIPELINE_CLIENT_FRONTEND_HOME`.
- OAuth and model-catalog state live there under
  `state/credentials_state.json`, `state/oauth_token.enc`,
  `state/oauth_token.lock`, `state/oauth_latest_report.json` and
  `state/model_catalog_state.json`.
- Temporary build/check artifacts are not product source and stay outside the
  source contract through local ignore rules.

## Structure

```text
Client Frontend/
|- client_frontend/
|- src/
|- server/
|- shared/
|- dev-tests/
|- runtime/
|- node/
|- README.md
|- README.txt
|- requirements.txt
|- start.bat
|- config.bat
|- installer.bat
|- build-runtime.bat
|- package.json
```

## Canonical Product Source

- `client_frontend/browser/`
  - Browser and UI product code for `main_app`, `config_app`, `render`, `api`,
    `types`, `chat_controller`, `config_select` and styles.
  - The `/config` surface edits `frontend_policy.json` through grouped editor
    fields inside one policy card.
- `client_frontend/http/`
  - HTTP server workflow and surface for `server/index.js`.
- `client_frontend/credentials/`
  - Server-side credential and OAuth ownership for login flow, sanitized
    session status, token state and LLM resolver.
- `client_frontend/model_catalog/`
  - Non-sensitive model-catalog ownership for `llm_shared` and `embeddings`,
    separate from provider I/O.
- `client_frontend/app_paths/`, `config/`, `provider/`, `vault/`,
  `chat_store/`, `memory/`, `min_agent/`, `runtime_paths/`
  - Peer server subsystems with explicit boundaries.

The active Corpus is never materialized in the module root. Fresh configs
default to the bundled demo DB:

```text
..\SampleDB\Consciousness Travel - Default Demo\Corpus\corpus.db
```

User selection remains user-configured and may be explicitly empty.

Page images are served preferably from the optional DB table
`document_page_images(document_id, page, content_type, image_blob)`.
The public image endpoint remains:

```text
GET /api/image/<docId>/<page>
```

Older corpora without embedded page images still work through the filesystem
fallback under `page_images/` relative to the active Corpus directory.

## Minimal Agent And Workbench

The read-only Minimal Agent offers:

- SQL
- document retrieval
- provenance inspection
- semantic search
- deterministic `database_coverage_snapshot`
- a tightly guarded local workbench

`database_coverage_snapshot` reads compact coverage facts from the active
Corpus so the Query Agent can explain materialization, promotions, fields,
rows, weak spots and release mix without starting a Kernel workflow or an
additional analysis cascade.

The workbench is deliberately narrow and read-only:

- Python runs through `server/workbench_python_runner.py` with read-only
  filesystem guards, no network, no process spawning, no native/registry writes
  and read-only SQLite except for `:memory:`.
- PowerShell is statically validated against a read-only allowlist before it
  runs through the bundled runtime.
- Writable cmdlets, network access, process starts, dynamic invocation and path
  traversal are outside the surface.
- Allowed read roots are the active Corpus under `MIN_AGENT_DATA_DIR`, the
  active DB under `MIN_AGENT_DB_PATH` and explicit config/soul files.
- PowerShell inherits the launcher/process environment and may inspect it
  through allowed read-only commands. This is an intentional local diagnostic
  capability, not a default query path.

## Path-Stable Root Surfaces

Browser:

- `src/main.ts`
- `src/config.ts`
- `src/main_app.ts`
- `src/config_app.ts`
- `src/ui/render.ts`
- `src/styles/main.css`

Server:

- `server/index.js`
- `server/min_agent.js`
- `server/provider.js`
- `server/config.js`
- `server/vault.js`
- `server/chat_store.js`
- `server/memory.js`
- `server/app_paths.js`
- `server/runtime_paths.js`
- `server/tokens.js`
- `server/vector.js`

## Runtime Model

- Start and config launchers run through `runtime/launch-server.bat`.
- Bundled runtimes remain under `node/` and `runtime/`.
- Runtime checker: `tools/check-runtimes.mjs`.
- Product start is host-independent: no production fallback to system Node,
  system Python or downloads.
- Bundled Python remains stdlib-only and exists only for the isolated read-only
  workbench runner.
- `config/config.json` remains OAuth-free. Access and refresh tokens must never
  appear in browser storage, query parameters or `GET /config/api/current`.
- A healthy OAuth session is the primary OpenAI LLM path. Embeddings and vector
  queries remain API-key based.
- `state-snapshot/` is an optional packaging/migration artifact from
  `tools/deploy.ps1 -IncludeStateSnapshot`, not product source. It can contain
  sensitive app-home state and remains outside version control.

## Taxonomy Agent Kernel Surface

The former Pipeline Manager is now the Taxonomy Agent in the UI. It talks to
the canonical Semantic Control Kernel workflow and support tool surface.

- Model-visible Kernel workflow/support tools keep intentionally empty object
  schemas, except `kernel_continue_resumable_workflow`.
- Paths, IDs, confirmations, recovery scope and other domain values are not
  written by the Agent as chat arguments.
- `kernel_continue_resumable_workflow` accepts only `resume_option_ref`, which
  must come from `kernel_resume_state.resume_options[]`.
- Permanent Kernel workflow/support tools are sent to MCP with `{}` as the
  argument object.
- Event-scoped recovery tools are injected only for the active Kernel mirror
  recovery event.
- A successful completed mirror clears stale recovery state from the active
  Taxonomy Agent surface.
- The retired action-surface model with generic wrapper tools must not be
  rebuilt in prompts or frontend routing.

## Kernel Event Transport

Browser and server communicate with the Kernel through the local HTTP bridge:

```text
GET  /api/v2/pipeline-manager/kernel/events
POST /api/v2/pipeline-manager/kernel/interactions/<interaction_request_id>/response
POST /api/v2/pipeline-manager/kernel/interactions/<interaction_request_id>/cancel
```

These routes poll `kernel.client_frontend_event_batch.v1`, relay
`kernel.user_interaction_response.v1` to the host-only bridge and never send
dialog values as chat messages to the Agent.

Important UI rules:

- Kernel-owned dialogs for input, selection, confirmation, blockers and
  recovery are rendered in the browser panel, not as Agent questions.
- Dialog submit/cancel immediately enters a local pending UI state to prevent
  duplicate submits.
- Pending interaction events are sticky/replayable until submitted, cancelled,
  closed, expired or superseded.
- Before each normal user chat turn the server reads `kernel_status` and
  reconciles volatile dialog/progress context with current Kernel truth.
- Terminal Kernel mirror events retire stale non-terminal progress fallback
  rows for the same `workflow_run_id`.
- Orchestrator snapshot progress can render individual stage rows for Intake,
  Optimizer, Interpreter, Validator, Normalizer, Corpus Builder and Embeddings.
- Live Error Cases appear as their own progress row and count recoverable
  source files under `Error Cases/**/originals/**`.
- `agent_explanation_guidance.response_mode = "explain_now"` starts a pure
  explanation turn. Workflow, support and recovery tools are hidden for that
  turn; the Agent may explain the current mirror event but must not start a new
  workflow.

## Recovery And Dialog Policy

- `kernel_cancel_active_run` is the only abort path for the Taxonomy Agent.
- It stops Kernel-owned background continuation process trees through persisted
  `*.ref.json` refs and marks active Kernel runs as `cancelled`.
- Kernel reset archives active Kernel runtime state and clears active database
  bindings/attach state.
- Kernel reset does not delete Corpus databases, Artifact Trees, Semantic
  Releases or owner-module files.
- Support-bundle hints and recovery options are rendered only from Kernel
  events and Kernel tool definitions.

## Debug Boundaries

Browser:

- `src/*.ts` and `src/styles/main.css` are stable entry surfaces.
- Actual browser logic lives under `client_frontend/browser/`.
- Bugs usually localize to `main_app`, `config_app`, `render`, `api` or
  `styles`.

Server:

- `server/*.js` are stable entry surfaces.
- Actual server logic lives under `client_frontend/http/`, `provider/`,
  `config/`, `vault/`, `chat_store/`, `memory/`, `min_agent/`,
  `runtime_paths/` and `app_paths/`.
- Bugs usually localize to HTTP, provider, config, vault, store, runtime or
  Minimal-Agent boundaries.

## Start, Build And Tests

Chat UI:

```bat
start.bat
```

Config UI:

```bat
config.bat
```

Runtime build:

```bat
build-runtime.bat
```

Dev tests:

```bat
dev-tests\bootstrap.bat
dev-tests\run-tests.bat
```

Central dispatcher:

```bat
..\run-dev-tests.bat --module "Client Frontend"
```

Runtime check:

```bat
node\node.exe --disable-warning=ExperimentalWarning tools\check-runtimes.mjs
```

## Deviation Log

| Module | Rule | Deviation | Reason | Risk If Open |
| --- | --- | --- | --- | --- |
| Client Frontend | MUST: reliable `module-manifest.json` | No `module-manifest.json` | The Frontend cannot honestly be represented as an Orchestrator action module without fake contract semantics | Federation audits must read this exception explicitly |
| Client Frontend | SHOULD: complete runtime rebuild from local sources | Full rebuild of all bundled third-party runtimes remains only partially reachable | The refactor hardens structure and product root, not every bundled foreign binary | Fully offline reproducible runtime builds remain partly dependent on host/artifact prerequisites |
| Client Frontend | SHOULD: root-near metadata lives in local package root | `shared/provider-catalog.json` stays outside `client_frontend/` | It is a deliberate root-near immutable contract source for browser and server | Changes must keep using the explicit adapter instead of distributed local copies |
| Client Frontend | MUST: no mutable Corpus truth in module root | Fresh configs default to the bundled demo DB under `..\SampleDB\...` | Live corpora are materialized outside the Frontend module root; the demo DB is shipped sample material | Without demo DB or user selection, the Minimal Agent must fail closed |
| Client Frontend | MUST: secrets are not accidental product artifacts | `state-snapshot/` can contain sensitive app-home transfer state | Optional deploy/install compatibility for fresh installs | Treat the snapshot as sensitive runtime transfer, not source |
| Client Frontend | SHOULD: read-only tool surfaces are understandable | PowerShell workbench may inspect launcher/process environment through allowed read-only commands | Local diagnosis should show the actual startup environment while writes/network/process paths remain blocked | Reviews may misclassify this as accidental drift without the explicit contract |
