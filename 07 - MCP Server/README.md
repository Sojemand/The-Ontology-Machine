# 07 - MCP Server

Local MCP control-plane server for The Ontology Machine.

## Role

- Standalone module with package root `mcp_server/`.
- Transport: local stdio MCP, no network surface.
- Purpose: tool catalog, self-description and owner-clear delegation to
  existing contracts in `00`, `01`, `03`, `04` and `05`.
- It is not a second business-logic host and not a raw-state writer.

## Owner Boundaries

The server calls mutating cross-module operations only through owner-local
contracts:

- `04 - Normalizer`: product contract and `normalizer_vision.edit_contract`.
- `01 - Optimizer`: product contract and `ingestion_layer_vision.edit_contract`.
- `03 - Validator`: `validator_vision.edit_contract` for dedicated Validator
  edit atomics.
- `05 - Corpus Builder`: product contract and `corpus_builder.edit_contract`.
- `00 - Orchestrator`: product, edit and admin contracts; no raw-state
  shortcuts.

The MCP Server itself does not write foreign state directly. Persistent domain
truth remains with the owning module. MCP-owned mutable truth is limited to
permission policy plus support/run helper state.

## Exposed Capability Families

The visible MCP capabilities exist because their owning module exposes them as
tested contract actions, or because they are explicit MCP control-plane helpers
without their own domain truth.

Major families:

- Workspace and Corpus context:
  - `prepare_pipeline_workspace_root`
  - `create_empty_corpus_db`
  - `activate_corpus_context`
  - `verify_workspace_active_release`
  - `inspect_active_workspace_status`
- Pipeline execution:
  - `run_active_pipeline`
  - `start_active_pipeline_run`
  - `inspect_active_pipeline_run`
- Semantic Release authoring:
  - `read_working_release`
  - `list_working_release_profiles`
  - `read_working_release_profile`
  - `validate_working_release`
  - `compile_working_release`
  - `preview_working_release_impact`
  - `create_working_release_package`
  - `export_working_release`
  - `derive_working_release_from_blueprint`
  - `create_minimal_custom_release`
  - `create_projection_draft`
- Locale and glossary:
  - `create_locale_scaffold`
  - `generate_locale_translation_payload`
  - `translate_working_release_locale`
  - `read_translation_glossary`
  - `upsert_translation_glossary_entry`
  - `remove_translation_glossary_entry`
- Owner edit surfaces:
  - `optimizer.*`
  - `validator.*`
  - `corpus_builder.*`
- Release activation and reset:
  - `activation_preflight`
  - `activate_release_on_existing_db`
  - `write_workspace_release_change_confirmation`
  - `write_workspace_db_reset_confirmation`
  - `reset_active_corpus_db`
- Runtime/admin:
  - `inspect_runtime`
  - `read_runtime_settings`
  - `write_runtime_settings`
  - `reset_runtime_settings`
  - `inspect_runtime_credentials`
  - `set_runtime_api_key`
  - `delete_runtime_api_key`
  - `reveal_secret`

`reset_active_corpus_db` always remains confirmation-gated.
`reveal_secret` requires the explicit unlock phrase
`REVEAL_SECRET:<target>` and is written to the Orchestrator audit trail.

## Delegation Map

- `corpus_builder.orchestrator_contract`
  - Corpus context, empty DB creation, active DB reset and release activation.
- `orchestrator.orchestrator_contract`
  - Pipeline run, context activation and read-only source-document inspection.
- `normalizer_vision.orchestrator_contract`
  - Default blueprint release export.
- `normalizer_vision.edit_contract`
  - Working release, projection, locale, glossary, validation, compile,
    preview and export steps.
- `ingestion_layer_vision.edit_contract`
  - Optimizer owner surfaces.
- `validator_vision.edit_contract`
  - Validator owner surfaces.
- `corpus_builder.edit_contract`
  - Corpus Builder authoring surfaces under `config/`.
- `orchestrator.admin_contract`
  - Runtime settings, credential metadata/API-key management and explicit
    secret reveal.

Semantic Release exports are not MCP-owned durable truth. Standalone export
requires an explicit `output_path` outside MCP `state/`. Workspace sequences
write releases under the relevant Corpus or workspace root.

## Workspace Sequences

Empty workspace DB:

```text
prepare_pipeline_workspace_root -> create_empty_corpus_db -> activate_corpus_context
```

Default blueprint archive:

```text
prepare_pipeline_workspace_root -> create_empty_corpus_db -> export_default_blueprint_release -> activation_preflight -> activate_release_on_existing_db -> activate_corpus_context
```

New DB from an exported release:

```text
create_empty_corpus_db -> activation_preflight -> activate_release_on_existing_db -> activate_corpus_context
```

New DB from existing pipeline artifacts:

```text
create_empty_corpus_db -> activation_preflight -> activate_release_on_existing_db -> activate_corpus_context -> rebuild_corpus_from_artifacts(replace_existing=false)
```

Special archive with custom working release:

```text
prepare_pipeline_workspace_root -> create_empty_corpus_db -> create_working_release_package -> export_working_release -> activation_preflight -> activate_release_on_existing_db -> activate_corpus_context -> verify_workspace_active_release
```

`activate_corpus_context` is only a path/context switch for active DB state. It
does not activate an extraction package, language or document profile.

## Semantic Control Kernel Cutover

The canonical Kernel surface exposed through MCP is the Semantic Control Kernel
bridge. The MCP Server starts the Kernel module through the local subprocess
contract:

```text
python -m semantic_control_kernel.orchestrator_contract
```

It does not import the sibling package directly.

Important rules:

- Normal `tools/list` exposes only the 16 permanent Semantic Control Kernel
  workflow/support names.
- Tool schemas are empty except `kernel_continue_resumable_workflow`, which
  accepts only the opaque `resume_option_ref` from
  `kernel_resume_state.resume_options[]`.
- Event-scoped recovery tools are invisible for normal Agent calls and are
  accepted only with an active Kernel mirror event scope.
- Host-only Client Frontend bridge operations are not Agent tools.
- Long Kernel continuations after user interaction run in a background
  continuation instead of blocking the stdio MCP call.
- The previous MCP-hosted legacy Kernel surface is retired.

The MCP Server does not build a second workflow world. Workflow decisions,
locks, receipts, recovery and resume belong to the Semantic Control Kernel.
Owner truth remains in owner contracts and their atomic MCP primitives.

## Normal Agent Path

Normal Agent work should use the Semantic Control Kernel workflow surface.
Atomic owner tools remain lower-level MCP primitives.

Retired generic scope surfaces are not part of the visible catalog:

- `inspect_extraction_packs`
- `check_working_release_readiness`
- `broaden_custom_release`
- `normalizer_source_action`

For working releases the safe authoring pattern is:

```text
Review -> Apply -> Validate -> Compile -> Export
```

Review tools do not write source state. Apply tools do not validate, compile,
export or activate. Export tools do not activate. Activation remains its own
preflight/confirmation/activation sequence.

## Pipeline Run Tools

`inspect_active_workspace_status` is the compact operational precheck for
"what is currently going on?". It reads stored Orchestrator context, counts the
registered `Input/` folder, summarizes the last MCP-started run and returns one
`next_action` hint. It does not replace detailed run inspection or governance
introspection.

`start_active_pipeline_run` is the normal chat-side start button for processing.
It reads stored Orchestrator context, checks the registered `Input/` folder,
starts the batch in the background and immediately returns a `run_id`.
`inspect_active_pipeline_run` then reports progress, runtime, log excerpts and
final result.

`run_active_pipeline` remains available as a synchronous blocking run for tests
or explicit automation.

If the MCP Server restarted after a background run and no longer owns a live
process handle, `inspect_active_pipeline_run` and `cancel_active_pipeline_run`
mark the run as `interrupted`. The server does not pretend that a cancel
succeeded and does not PID-reattach blindly.

## Agent Permissions

The server exposes an Edit Suite surface:

```text
mcp_server.agent_permissions
```

It writes only `config/agent_permissions.json` in the MCP Server module. The
policy is evaluated before every tool call.

Permission levels:

- `L0_READONLY`: inspection, read surfaces, read-only Corpus diagnostics and
  the shared Semantic Control Kernel transport surface.
- `L1_AUTHOR`: working-release reads, validation, compile, export, glossary
  reads and safe authoring checks without runtime-state changes.
- `L2_OPERATOR`: source-authoring apply, glossary upsert/remove, Corpus
  context, release activation, rebuild, merge, reset and embeddings.
- `L3_ADMIN`: owner-surface writes, runtime settings, credentials and audited
  secret reveal.

The active level comes from `VISION_MCP_AGENT_LEVEL`; without an environment
value, `default_agent_level` applies. `maximum_agent_level` is a hard cap so an
Agent cannot raise itself above the Edit Suite policy.

## Support Monitor And Bug Reports

Installed runtime builds do not patch product code directly and do not require
Git. The retired `support_incident_workflow` bundle surface is replaced by an
atomic sequence:

```text
assess_support_incident -> preview_support_bug_report -> build_support_bug_report -> queue_support_bug_report
```

Additional helpers:

- `list_support_incidents`
- `dismiss_support_incident`

Only product-like classes such as `unexpected_exception`,
`contract_regression`, `repeatable_product_failure` and
`data_corruption_risk` may produce a reportable `assessment_id`.
Setup/input/environment failures should be explained as such instead of being
queued as product bug reports.

## Start

```bat
run.bat
```

The server speaks MCP over `Content-Length` framed JSON-RPC messages on
stdin/stdout.

Tool catalog without server loop:

```bat
run.bat --list-tools
```

Runtime preflight:

```bat
check-runtime.bat
```

`check-runtime.bat` runs strictly against the bundled runtime.
`mcp_server.healthcheck` can enforce the same check with `strict_runtime=true`;
without that switch it remains useful from the local test venv for development
diagnostics.

## Mutable Artifacts

Server-owned mutable state lives under:

```text
state/
```

The server writes only its own working artifacts there, such as temporary
contract-call files, pipeline-run metadata or support reports. Semantic Release
bundles belong in explicit user, Corpus or workspace target paths.

## Dev Tests

```bat
dev-tests\bootstrap.bat
dev-tests\run-tests.bat
```

The suite checks catalog governance, MCP framing, owner delegation and the
path-stable healthcheck contract.

## Deviation Log

Some path-stable MCP surfaces and regression tests remain above the preferred
file-size guidance because they each carry a coherent surface or dense
regression block. Splitting them only for numeric compliance would currently be
more redistribution than simplification. Revisit only through path-stable
refactors with matching regression coverage.
