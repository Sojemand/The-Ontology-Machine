# 03 - Validator Vision

Host-only Validator for `structured.json` produced by the vision, file and
table Interpreter paths.

## Purpose

- Validates single `structured.json` files or complete folders.
- Dispatches strictly through `processing.interpreter_profile`.
- Checks vision documents against context, fields, rows and
  `content.free_text`.
- Checks file documents against canonical raw evidence from `*.raw.json`.
- Checks table documents against deterministic table truth from the active
  Optimizer slot.
- Writes exactly one JSON report per document.

## Operation

- The only debug GUI lives in `00 - Orchestrator`.
- The module exposes only the file-based contract
  `validator_vision.orchestrator_contract` plus runtime and installer helpers.
- The additive debug path is headless through `debug_run` and writes only under
  the `session_root` assigned by the host.
- Production contract actions `validate_document` and `healthcheck` remain
  stable.

## Runtime And Paths

- Self-contained runtime under `runtime/python`.
- Runtime rebuild expects an explicit portable Python source through root
  tooling, `-SourceRuntime` or `tools/python-runtime-source`.
- Runtime rebuild and per-user installers publish immutable app/runtime trees
  from stage folders and roll back to the previous state when runtime checks
  fail.
- Mutable data defaults to
  `%LOCALAPPDATA%\Enterprise Stack\Validator Vision`.
- Debug Host session-local home overlay uses `VALIDATOR_VISION_HOME`.
- Local defaults remain under `config/config.json`.

| Path | Role | Mutable |
| --- | --- | --- |
| `validator_vision/` | Product code and contract surfaces | no |
| `runtime/` | Portable runtime and packaging metadata | no after build |
| `config/config.json` | Bundled defaults | no |
| `%LOCALAPPDATA%\Enterprise Stack\Validator Vision` | Product config, logs, state and output home | yes |

## Orchestrator Contract

- `validate_document`
  - Production single-file request with `structured_path`,
    `validation_output_path` and optional `raw_path`.
  - `raw_path` is the canonical raw-backed evidence path for `file` and
    `table`.
- `healthcheck`
  - Runtime and contract self-check.
- `debug_run`
  - Headless debug path for the Orchestrator.
  - Required fields: `action`, `mode`, `session_root`, `output_root`.
  - `output_root` must stay inside `session_root`; foreign write targets fail
    closed.
  - `single`: `source_path`.
  - `batch`: `input_root`.
  - Optional `options`: `raw_evidence.raw_path`, `raw_evidence.raw_root`,
    `check_toggles`.

Debug session artifacts:

- `request.json`
- `response.json`
- `snapshot.json`
- `result.json`
- `run.log`
- `cancel.request`
- `outputs/validation_reports/*.vision_validation_report.json`
- `outputs/validation_reports/*.files_validation_report.json`
- `outputs/config_snapshot.json`
- `outputs/report_index.json`

## Internal Surfaces

- `validator_vision.orchestrator_contract`: stable subprocess surface for the
  Orchestrator and Debug Host.
- `validator_vision.edit_contract`: owner-local edit surface for
  `06 - Edit Suite`.
- `validator_vision.validator`: validation logic.
- `validator_vision.main`: internal headless CLI for `validate` and
  `validate-batch`; no local GUI or maintenance surface.

## Edit Suite

- Owner-local edit contract: `validator_vision.edit_contract`.
- Additive fast-path action: `read_bundle` for the Edit Suite; product contract
  and manifest actions remain unchanged.
- Edit surfaces:
  - `validator.settings`
  - `validator.report_preview_policy`
  - `validator.debug_capabilities`
- `validator.settings` and `validator.report_preview_policy` write
  owner-locally into mutable `config/config.json` under the app home.
- `validator.debug_capabilities` mirrors read-only manifest truth for contract
  and debug capabilities.
- Report files and debug session artifacts are intentionally outside the edit
  contract.

## Development

Runtime check:

```bat
check-runtime.bat
```

Per-user installation:

```bat
installer.bat
```

Dev tests:

```bat
dev-tests\bootstrap.bat
dev-tests\run-tests.bat
```

Installer stage/compile:

```bat
build-installer.bat --skip-runtime-build
build-installer.bat --skip-runtime-build --compile
```

`--compile` requires Inno Setup 6 (`ISCC.exe`) on the build machine.

## Reports

Each document produces exactly one profile-dependent report:

- Vision: `*.vision_validation_report.json`
- File: `*.files_validation_report.json`
- Table: `*.vision_validation_report.json`

Possible results:

- `PASS`
- `WARN`
- `FAIL`

## Safety Limits

- JSON inputs are size-limited to 16 MiB before loading.
- `structured.json` must keep expected container shapes for `content`,
  `context`, `source`, `processing`, `content.fields` and `content.rows`;
  invalid shapes fail closed.
- Batch discovery stops above 5000 `*.structured.json` files.
- Raw indexing stops above 5000 `*.raw.json` files.
- Auto-derived report file names are shortened and hashed for Windows path
  budgets.
- Broken raw files in `raw_root` are not silently swallowed; failed raw
  resolution reports the skipped raw-file count.
- `debug_run` builds `report_index.json` and response outputs only from the
  current run's reports; stale session files are not reconstructed as current
  runtime truth.
- File-raw claims ignore isolated OCR-edge page numbers in multipage documents
  so footer/page labels such as `21` do not fail as missing domain claims.
  Table cells and non-isolated values remain claim-relevant.

## Regression Coverage

- Dev tests cover contract, runtime, installer, edit-contract and path
  boundaries.
- Golden-report regressions exist for vision, file and table profiles.
- The table profile is tested against raw-backed claims through
  `deterministic_extract.tables_base`.

## Deviation Log

| Module | Rule | Deviation | Reason | Owner | Follow-up Date | Risk If Open |
| --- | --- | --- | --- | --- | --- | --- |
| 03 - Validator | SHOULD: regressions with realistic or real artifacts | Golden regressions for vision/file/table exist; the real anonymized document corpus remains small | real customer documents are not yet released as versioned fixtures | Pipeline Cleanup | 2026-05-15 | rare document variants may drift later |
