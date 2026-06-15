# Edit Suite

Standalone Windows desktop surface for module readiness, drift inspection and
owner-local configuration surfaces.

## Role

- Federation module under `06 - Edit Suite`.
- User-facing desktop application.
- Generic edit shell, not a pipeline runner and not a debug host.
- Starts even when some sibling modules do not yet expose migrated
  `edit_contract` surfaces.
- Governance role: `frontend_module` / owner-local desktop control surface.

## Runtime Build

- Target platform: Windows x64.
- Bundled runtime: CPython 3.11 x64.
- Offline source for runtime packages: `runtime/wheelhouse`.
- Runtime contract: `runtime/runtime-manifest.json`.
- Runtime preflight: `run.bat` checks bundled runtime provenance before the GUI
  starts.
- Owner contract timeout: default `1800` seconds, override with
  `EDIT_SUITE_OWNER_CONTRACT_TIMEOUT_SECONDS`.

```bat
build-runtime.bat
check-runtime.bat
```

## Per-User Installation

- Install target: `%LOCALAPPDATA%\Programs\Vision Pipeline\06 - Edit Suite`.
- No administrator rights required.
- No host Python required for operation.
- `state/` remains mutable and upgrade-stable.

```bat
build-installer.bat
build-installer.bat --compile
```

## Behavior

- Discovers direct sibling modules `00` through `07`; `06 - Edit Suite` and
  `Client Frontend` are intentionally excluded from owner-module discovery.
- Starts cached-first from `state/registry_cache.json` and the suite-local
  bundle cache under `state/bundles/*.json`.
- Live discovery and owner-local surface refresh run asynchronously in the
  background, so the shell remains renderable during startup.
- Prefers owner-local `read_bundle`; legacy modules fall back to
  `describe_surfaces` plus `read_surface`.
- Real `read_bundle` contract errors remain visible and are not hidden as
  legacy fallback.
- Shows visible readiness/drift states plus lazy-loaded owner-provided edit
  surfaces for ready modules.
- Renders contract and bundle errors in the GUI instead of hiding them behind an
  empty tab state.
- Never writes into foreign module state directly.
- Persists suite-local state only under `state/`.
- Runs owner actions as UI background jobs with token-based stale-result
  protection. The hard runtime boundary remains the owner contract timeout.
- Long UI scans, especially Semantic Release artifact scans, are bounded and
  asynchronous; scan limits are reported visibly instead of blocking the shell.

## Mutable Truths

- `state/ui_state.json`: window state, selection and operational form context.
- `state/registry_cache.json`: cached-first discovery state; corrupt JSON
  triggers live rebuild.
- `state/bundles/*.json`: cached owner bundles; corrupt JSON triggers live
  reload.
- `state/corpus-db-confirmations/` and `state/merge-confirmations/`:
  suite-local, path-validated owner-action confirmation artifacts.
- `state/edit-contract-*`: temporary contract I/O directories; old leftovers
  are cleaned best-effort.

## Development

```bat
dev-tests\bootstrap.bat
dev-tests\run-tests.bat
```

Or from the repository root:

```bat
..\run-dev-tests.bat --module "06 - Edit Suite"
```

## Golden-Path Evidence

- Contract surface: `dev-tests/tests/test_contract.py`.
- Runtime and installer: `dev-tests/tests/test_packaging.py`.
- Live registry: `dev-tests/tests/test_registry.py`.
- Owner bundles: `test_as_built_blueprint.py`,
  `test_orchestrator_contract.py`, `test_interpreter_vision_contract.py`,
  `test_validator_contract.py`, `test_normalizer_contract.py`,
  `test_corpus_builder_contract.py`, `test_mcp_server_contract.py`.
- UI action and state safety: `test_operation_runner.py`,
  `test_repository.py`, `test_surfaces_read_bundle.py`.

## Deviation Log

No open Edit Suite deviations are currently documented in this README.
