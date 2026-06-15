# Optimizer

`01 - Optimizer` is the unified Optimizer module of The Ontology Machine
pipeline. It owns a single public federation slot with
`module_key = "optimizer"` and processes documents through two profiles:

- `vision`: image-heavy and scan-heavy documents, with LLM OCR through the
  orchestrator-owned `optimizer_ocr` runtime edge.
- `file`: born-digital PDFs, Office files, mail formats, Markdown, plain text
  and other file-native extraction paths.

## Package Structure

The three visible package names are current architecture, not legacy leftovers:

- `ingestion_layer_vision`: scan, image and visually rendered input path. It
  owns the public Orchestrator contract and dispatches profile selection.
- `ingestion_layer_file`: born-digital file path for native PDF text, Office,
  mail, Markdown/text and plugin extraction.
- `optimizer_ocr`: vision-layer port for model-backed OCR calls. It normalizes
  LLM OCR output and is used for page assets, scan fallback OCR and embedded
  image routes.

Vision and file handling used to be separate modules. They are now merged
because classification, artifact policy, runtime packaging, debug contracts and
downstream raw evidence are all Optimizer responsibilities. The split remains
visible internally as processing paths; externally the federation slot is still
only `optimizer`.

## Contract

- Entry point: `ingestion_layer_vision.orchestrator_contract`.
- Actions:
  - `classify_document`
  - `extract_document`
  - `healthcheck`
  - `scan_debug_input`
  - `debug_run`

Canonical raw output:

- Vision profile: `schema_version = "optimizer_raw_v2"`.
- Vision raw contains only `source`, `extraction`, `metadata`, `context` and
  `ocr_reference.blocks`.
- Required field: `optimizer_profile = "vision" | "file"`.

`classify_document` is the public profile gate. It validates `source_path` and
returns the recommended `optimizer_profile` for the following
`extract_document` run. Image files and scan PDFs go through `vision`;
born-digital PDFs and file-native formats go through `file`.

Production `extract_document` calls keep `source_path`, `raw_output_path` and
`page_assets_dir` strictly inside the roots provided by the Orchestrator. The
single-file `debug_run` mode treats `source_path` as the only input truth and
must not be blocked by stale or missing `input_root`. Scan and batch debug
modes still require a valid `input_root`.

The vision response returns:

- `document_raw_path`
- `page_raw_paths`
- `page_asset_paths`

`page_asset_paths` are working paths for the active Interpreter run. They are
not serialized into the persistent raw files.

In the file profile, native extractor text remains the only text authority.
Renderer text may be used only for page assets and text-neutral page/span
assignment; it must not replace the native extracted value.

## Runtime

Immutable payload:

- `ingestion_layer_vision/`
- `ingestion_layer_file/`
- `runtime/`
- `plugins/`
- `tools/`
- `module-manifest.json`

Mutable runtime data:

- `%OPTIMIZER_HOME%`
- `%LOCALAPPDATA%\Enterprise Stack\Optimizer`
- source-slot fallback `.appdata/`

Expected mutable folders:

- `config/`
- `state/`
- `output/`
- `logs/`

`runtime/python` is the local portable CPython runtime. `check-runtime.bat`
validates the runtime contract. `tools/build-runtime.bat` is development and
packaging tooling only. The module is headless and has no local product
launcher.

## Edit Suite

Owner-local surfaces for `06 - Edit Suite`:

- `optimizer.settings`
- `optimizer.ocr_prompt`
- `optimizer.output_contract_preview`
- `optimizer.debug_capabilities`

`optimizer.settings` is shown as a grouped form for processing and rendering
settings. `optimizer.ocr_prompt` edits `config/optimizer_ocr_prompt.md`; the
prompt must keep `{page_count}` and may use `{source_filename}` or
`{source_filename_sentence}`.

`optimizer.output_contract_preview` is read-only and mirrors raw schema,
profile selection, response paths, page-asset policy and the `optimizer_ocr`
owner boundary. Projection catalogs, domain routing signals, provider/model
selection and OCR secrets remain Orchestrator-owned or downstream-owned.

## LLM OCR

Production OCR runs through the central `optimizer_ocr` port:

- Vision image routes, scan fallback OCR, mail-child OCR and DOCX embedded image
  OCR use `optimizer_ocr.extract_page_assets`.
- The port expects rendered page assets and normalizes model output into the
  existing OCR result payload.
- Persistent `ocr_reference.blocks` remain token-light: `id`, `type`, `value`,
  optional layout/confidence hints and `formatting` only when `bold=true`.
- Local OCR plugin folders, GPU/CPU paths and old local OCR readiness rules were
  removed.
- Provider, model, token budget, timeout and secret arrive only through
  ephemeral `OPTIMIZER_OCR_*` environment values from the Orchestrator.
- OpenAI OAuth uses the same ChatGPT/Codex SSE backend call shape as the
  Interpreter. API-key modes use the configured provider endpoint
  (`/responses` or `/chat/completions`).

## Packaging

- Per-user install target:
  `%LOCALAPPDATA%\Enterprise Stack\Optimizer\app`.
- `installer.bat`, `check-runtime.bat` and `build-installer.bat` validate source
  slot and target installation.
- OCR is an LLM dependency of the `vision` profile (`optimizer_ocr`). The
  installer validates only the portable runtime contract; there is no local GPU
  or OCR check.
- `.pst` and `.ost` prefer the bundled `mail-outlook-store` plugin runtime with
  `pypff`; Outlook/MAPI remains only an optional file-profile fallback.

## Tests

```bat
dev-tests\bootstrap.bat
dev-tests\run-tests.bat
```

The development suite checks contract behavior, packaging, runtime and selected
raw/routing invariants of the unified module.
