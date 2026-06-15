# 04 - Normalizer

`04 - Normalizer` reads `*.structured.json`, selects a taxonomy projection and
writes exactly one `*.structured.normalized.json` per input file.

## Purpose

- Canonical second view for retrieval, validation and Corpus building.
- Release-owned projection routing from local projection assets.
- Semantic Release and Runtime Semantic Assets for downstream modules.
- Headless operation through the Orchestrator contract.

## Projection Release Contract

- `SPEC_Projection_Release.md` is the root execution basis for release-driven
  projection routing.
- Release-owned routing markers live in projection files under
  `routing.surface_signals`.
- `surface_signals` contains exactly `text_markers`, `domain_markers`,
  `section_roles` and `party_roles`.
- `build_semantic_release` validates these projection signals fail-closed.
- `build_runtime_semantic_assets` compiles them into
  `semantic_extraction_policy_v2` without changing the top-level
  `runtime_semantic_assets_v1` format.
- Runtime bundle OCR defaults declare only the Orchestrator-governed
  `optimizer-llm-ocr` port plus scan, vision-route and rendering parameters.
  Local Paddle/GPU/CPU/device fallback policies are invalid legacy state.
- `projection_routing` arbitrates between local evidence and Interpreter hints.
- `projection_hint_mode=advisory` remains the default.
- `projection.selection.reason` is the visible explanation surface for local
  score state, hint priority and rejection reason.

## Public Contract

`module-manifest.json` exposes these actions:

- `normalize_document`
- `build_projection_catalog`
- `build_runtime_semantic_assets`
- `publish_semantic_release`
- `list_default_blueprints`
- `export_default_blueprint_release`
- `create_zero_shot_working_release`
- `healthcheck`
- `debug_run`

Important invariants:

- No manifest or action drift.
- Unknown request fields are rejected for all public contract actions.
- `normalize_document`, `healthcheck` and `debug_run` require
  `runtime_settings`.
- `normalize_document.structured_path` must end in `*.structured.json`;
  `normalized_output_path` must be a JSON file.
- `debug_run` rejects debug roots under `config/`, `runtime/`, `vendor/` or the
  module root.
- `build_runtime_semantic_assets` accepts only `action` plus a complete Semantic
  Release payload.
- `publish_semantic_release` exports only from saved owner files.
- Preview, single-run and batch routing use the same arbitration logic.
- Model responses must provide top-level `processing`, `classification`,
  `context` and `content` sections as JSON objects; missing sections are not
  silently normalized to `{}`.

Schema modes:

- API-key providers use `json_schema` with `strict=true` when the active schema
  is strict-compatible.
- If a strict schema is rejected by the transport, that attempt falls back to
  `json_object`; the local parser still fails hard on missing top-level
  sections.
- OpenAI OAuth currently runs through the Orchestrator-owned backend transport
  with `json_object`; auth, model and token budget remain request-owned and are
  not persisted locally.

## Local Config And Assets

`config/config.yaml` contains only project-local values:

- `timeout_seconds`
- `max_retries`
- `retry_delay_seconds`
- `structured_outputs`
- `default_workers`
- `max_structured_bytes`
- `max_batch_files`
- `max_batch_workers`
- `taxonomy_profile_id`
- `projection_hint_mode`
- `projection_routing.*`

Local assets under `config/`:

- `prompt_bundle.json`
- `prompt_overrides.json`
- `taxonomy_sources/<release_id>/`
- `semantic_release.recipe.json`

Release-related truth:

- `config/taxonomy_sources/<release_id>/` is the source-first authoring layer
  for release, master and projection core/text files.
- Step 3 compiles this source package fail-closed into release-ready payloads in
  memory.
- The release recipe remains the legacy activation surface; `release_id`,
  `release_version` and `projection_ids` must match the active `release.yaml`.
- Runtime fields such as `model`, `max_output_tokens` and auth remain
  request-owned and are not stored locally.

## Edit Contract

Entry point:

```bat
python -m normalizer_vision.edit_contract --request <request.json> --response <response.json>
```

Visible surfaces:

- `normalizer.settings`
- `normalizer.prompt_overrides`
- `normalizer.prompt_bundle`
- `normalizer.taxonomy_master`
- `normalizer.taxonomy_profiles`
- `normalizer.translation_glossary`
- `normalizer.semantic_release_authoring`
- `normalizer.debug_capabilities`

Owner rules:

- `normalizer.settings` owns `projection_hint_mode` and
  `projection_routing.*`.
- `config/taxonomy_sources/<release_id>/` is the authoring truth for
  release-driven builds.
- `normalizer.taxonomy_master` writes `master.core.yaml` and
  `master.text.en.yaml`.
- `normalizer.taxonomy_profiles` writes
  `projections/<projection_id>.core.yaml` and `.text.en.yaml`.
- `normalizer.translation_glossary` may write
  `translation_glossary.en.yaml` as an `authoring_only` surface for English
  control terminology.
- `normalizer.semantic_release_authoring` writes `release.yaml` and syncs
  `config/semantic_release.recipe.json` additively.
- Export and activation validate the source package first, compile
  release-ready payloads in memory and pass only exported `.json` release
  bundles to `05 - Corpus Builder`.
- Bootstrap and data-informed review tools remain read-only. Apply tools mutate
  only the source-first working package. Exported Semantic Release artifacts
  change only after validate/compile/export steps.
- Locale tools currently accept only the internal control locale `en`.
- `normalizer.debug_capabilities` is read-only.

## Debug And Orchestrator Paths

- Product operation runs only through
  `normalizer_vision.orchestrator_contract`.
- `debug_run` is the only run/debug surface for the Orchestrator host.
- `build_projection_catalog` remains a local legacy/admin/debug path for
  source-backed release analysis.
- The generic Debug Host discovers capabilities through `module-manifest.json`.

## Runtime And Packaging

- `build-runtime.bat` builds `runtime/python` offline from shipped artifacts.
- `check-runtime.bat` validates runtime and module contract.
- `installer.bat` installs the module slot under
  `%LOCALAPPDATA%\Programs\Vision Pipeline\04 - Normalizer`.
- Mutable data remains `config/config.yaml`, `output/` and `state/`.
- `runtime/` is not the owner for projection routing and is not maintained
  manually for that semantics.

## Production Readiness

- `check-runtime.bat` and `dev-tests\run-tests.bat` are the runtime/dev gates.
- Local mutable artifacts under `output/`, `state/`, `.tmp` and pytest cache
  folders are not part of the installer/runtime contract and are not deleted
  automatically.

## Tests

```bat
dev-tests\bootstrap.bat && dev-tests\run-tests.bat
```

Directly with the suite Python:

```bat
dev-tests\.venv\python.exe -m pytest dev-tests\tests
```

The suite covers:

- Semantic Release, Runtime Semantic Assets, Projection Routing and hint
  arbitration.
- Edit Contract and contract/packaging boundaries.

Cross-module ratchets in `tools/dev-tests` additionally check:

- The `04` compiler result against the checked-in `01` fixture and the
  published `05` release mirrors.
- Terminology and LOC drift between SPEC, README and Edit Contract.

## Governance

- README, Edit Contract, slot summary and tooling use the same vocabulary:
  `routing.surface_signals`, `semantic_extraction_policy_v2`,
  `projection_routing`, `projection_hint_mode=advisory`,
  `projection.selection.reason`.
- `runtime/` and other mirrors remain untouched by this routing semantics.
- Sibling modules consume only `runtime_semantic_assets_v1`,
  `projection_catalog`, `context.projection_hint` and
  `projection.selection`.

## Phase 19 Semantic Release Domain Service

- The Phase 19 owner lives only in `normalizer_vision`.
- No `normalizer_file` owner exists and no database attach/activate step moved
  into the Normalizer.
- Edit-contract owner actions:
  - `materialize_custom_taxonomy_artifact`
  - `materialize_custom_projection_artifact`
  - `apply_taxonomy_update_state`
  - `apply_projection_update_state`
  - `remove_taxonomy_from_release`
  - `remove_projection_from_release`
  - `validate_projection_binding`
  - `compile_semantic_release_candidate`
  - `merge_semantic_release_candidates`
- Creation precursor payloads are accepted only by `materialize_*`; executable
  mutation payloads only by `apply_*_update_state`.
- Family-confused payloads fail closed.
- Normalizer owner outputs return detached refs, diagnostics and fingerprints
  only and do not mutate Corpus Builder database state.
