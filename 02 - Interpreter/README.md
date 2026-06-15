# Interpreter

`02 - Interpreter` is the unified Interpreter module of The Ontology Machine
pipeline. It owns a single public federation slot with
`module_key = "interpreter"` and consumes the canonical
`interpreter.request.json` contract for two profiles:

- `vision`: image-heavy and OCR-heavy requests.
- `file`: born-digital and file-native requests.

The downstream field `processing.interpreter_profile` intentionally remains
stable and is still either `vision` or `file`.

## Contract

- Entry point: `llm_interpreter.orchestrator_contract`.
- Actions:
  - `interpret_document`
  - `healthcheck`
  - `debug_run`
  - `generate_llm`

The production request shape is unified. Legacy request shapes such as `pages`
and `file_reference` are no longer part of the product contract.

`generate_llm` is the generic provider bridge used by the Semantic Control
Kernel. It accepts messages, optional JSON schema and runtime settings from the
Orchestrator, uses only ephemeral Orchestrator-injected authentication and
returns a `kernel.llm_provider_response.v1` compatible response.

## Runtime

Immutable payload:

- `llm_interpreter/`
- `runtime/`
- `tools/`
- `module-manifest.json`

Mutable runtime data:

- `%INTERPRETER_HOME%`
- `%LOCALAPPDATA%\Enterprise Stack\Interpreter`
- source-slot fallback `.appdata/`

Expected mutable folders:

- `config/`
- `state/`
- `output/`
- `logs/`

`config/.env` contains only owner-local, non-sensitive runtime and limit
values. Authentication, model selection and `max_output_tokens` remain
Orchestrator-owned. `generate_llm` must not read or persist module-local
credentials; it runs through the same `VISION_PROVIDER_*` environment contract
as `interpret_document` and `healthcheck`.

## Edit Suite

Owner-local surfaces for `06 - Edit Suite`:

- `interpreter.runtime_policy_env`
- `interpreter.execution_limits`
- `interpreter.prompt_bundle`
- `interpreter.output_contract_preview`
- `interpreter.debug_capabilities`

These surfaces apply to both profiles of the unified module. Profile
differences live in Interpreter logic and in the request payload, not in
separate module slots. The editable prompt bundle lives under
`config\prompt_bundle\`.

## Packaging

- Per-user install target:
  `%LOCALAPPDATA%\Enterprise Stack\Interpreter\app`.
- `tools\build-runtime.bat` builds and validates the portable runtime for
  development and packaging.
- `installer.bat`, `check-runtime.bat` and `build-installer.bat` validate source
  slot and target installation.
- The runtime remains headless and ships no Tcl/Tk.
- Production authentication is expected only through Orchestrator-owned runtime
  environment.

## Tests

```bat
dev-tests\bootstrap.bat
dev-tests\run-tests.bat
```

The development suite checks contract behavior, prompt bundle handling,
runtime, packaging and the unified edit contract.
