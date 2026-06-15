# README.operations

Additional operation and build notes for `05 - Corpus Builder`.

## Runtime And Build

Local module start:

```bat
check-runtime.bat
runtime\python\python.exe -m corpus_builder --help
```

Build or validate the portable runtime:

```bat
build-runtime.bat
build-runtime.bat --validate-only
..\tools\build-runtimes.bat --module "05 - Corpus Builder"
..\tools\build-runtimes.bat --module "05 - Corpus Builder" --validate-only
```

Expected runtime paths:

- `runtime/python`
- `runtime/runtime-manifest.json`
- mutable product data in `state/` and `output/`

## Development

Product source lives only under the module itself. Do not use these as primary
source:

- `dist/`
- `runtime/`
- `.venv/`
- `venv/`
- `__pycache__/`
- `.pytest_cache/`
- `.pytest-tmp/`
- `.tmp/`

Run local tests with CPython `3.11.x`:

```bat
dev-tests\bootstrap.bat
dev-tests\run-tests.bat
```

The suite uses a short per-run basetemp under `%TEMP%\om-cb-pytest-*`.
`PYTEST_BASETEMP` may override that path for targeted local diagnosis.

## Semantic Release

- `load-release` stages only an exported `.json` release bundle.
- `apply-release` activates the already published bundle state for exactly one
  `corpus.db`.
- Kernel-backed attach/activation calls may set `write_global_mirrors=false`.
  Then Corpus Builder validates the provided release and writes only the
  target-specific DB activation; owner-local Published/Active/Report mirrors
  remain unchanged.
- `semantic_status` and `read_active_semantic_release` also report whether the
  active release file and DB `installation_state` match.
- Release fingerprint changes mark active documents as `stale`.
- After that, run `backfill-stale` or perform a complete rebuild.

Hard guardrails:

- No stage/apply path for directories, YAML files or other non-`.json` release
  sources.
- No stage/apply path for release bundles whose fingerprint drifts from their
  content.
- No `apply-release` for active documents without `projection_id`.
- No `apply-release` when projections are missing in the new release.
- No `apply-release` across different master taxonomy lines.
- Normalized-first loads are blocked without a compatible active release.

## Rebuild From Artifacts

Preferred rebuild input:

- Artifact folder with `normalized/`, `structured/`, `validation/`.
- Optional sibling `page_images/` for DB image persistence.
- Recursive scan over pipeline clusters such as `vision/...`.

Important rules:

- `normalized` is the primary rebuild basis.
- `structured` and `validation` are included only as a complete evidence pair.
- `runtime\python\python.exe -m corpus_builder rebuild` remains the direct CLI
  rebuild path.
- The Orchestrator Debug Host uses the same artifact model through
  `scan_debug_input` and `debug_run`.
- `debug_run` with `mode=single` loads exactly one
  `*.structured.normalized.json` into a fresh session DB.
- `debug_run` with `mode=batch` rebuilds `outputs/corpus.db` from an artifact
  folder.

## Edit Suite Surface

The local GUI was removed. Module-near work surfaces for:

- Semantics
- Search
- Statistics
- Export
- Artifact rebuild

are provided through the Corpus Builder slot in `06 - Edit Suite`.
The Orchestrator Debug Host remains responsible for `scan_debug_input` and
`debug_run`.

The Edit Suite exposes only:

- `corpus_builder.settings`
- `corpus_builder.embeddings_policy`
- `corpus_builder.search_policy`

Semantic stage and activation run as actions through `Settings`.

## Installer

```bat
build-installer.bat
build-installer.bat --compile
```

The installer targets user-writable paths under:

```text
%LOCALAPPDATA%\Programs\Corpus Builder Vision
```
