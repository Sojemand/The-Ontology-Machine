# 08 - Semantic Control Kernel

Headless control module for the Semantic Control Kernel workflow layer.

## Role

- Module archetype: `control_module`.
- Package root: `semantic_control_kernel/`.
- Public product surface: `semantic_control_kernel.orchestrator_contract`.
- Canonical workflow source: `../Semantic Kernel SPEC/`.
- Governance source: `../SPEC_Handover_Blueprint.md`.
- Build plan: `SPEC_Semantic_Control_Kernel_Build.md`.

The Semantic Control Kernel owns workflow semantics, state transitions, user
interaction contracts, recovery classification, resume state, receipts and
Pipeline adapter orchestration.

The module does not own document transformation, semantic release authoring
primitives, Corpus database internals, MCP transport, or Client Frontend UI
dialogs. Those remain owner-local to their modules and are reached only through
documented contracts.

## Current Status

Current manifest status value: `agent_surface_shell`.

The manifest label remains stable for the earlier surface-contract tests, but
the module now contains the Phase 9 through Phase 19 workflow and adapter
implementation, the Phase 13 recovery surface, the Phase 18 observability
bundle and the Phase 20 go-live evidence harness.
The earlier Phase 7 `workflow_not_implemented` shell is no longer the live
runtime truth; the permanent Agent-facing tools now route into current
owner-phase handlers and fail closed only on real missing Kernel state or
policy blockers.

- `module-manifest.json` exposes the 16 permanent Agent-facing workflow and
  support/control actions only.
- `semantic_control_kernel/surface/agent_tools.py` and
  `semantic_control_kernel/surface/mcp_tool_schemas.py` are the canonical
  public tool inventories for Agent-visible, event-scoped, internal and
  continuation-only names.
- `semantic_control_kernel/orchestrator_contract.py` is the subprocess
  bridge entrypoint used by `07 - MCP Server`.
- Owner-local mutation remains in Orchestrator, Normalizer and Corpus Builder
  behind adapter boundaries; the Kernel still owns workflow routing, dialogs,
  blockers, recovery policy, receipts and resume state.
- Phase 8 LLM functions are executed through `KernelLLMPort` and
  `OrchestratorHostedLLMAdapter`. The Kernel renders prompts, validates
  outputs and writes LLM artifacts, but provider credentials, provider family
  and model selection come only from the Orchestrator
  `semantic_control_kernel_llm` runtime profile.
- Phase 20 handoff evidence is written under
  `release/go_live/<go_live_run_id>/`.

## Local Structure

```text
08 - Semantic Control Kernel/
|- semantic_control_kernel/
|- dev-tests/
|- runtime/
|- config/
|- state/
|- tools/
|- README.md
|- requirements.txt
|- module-manifest.json
|- build-runtime.bat
|- check-runtime.bat
|- SPEC_Semantic_Control_Kernel_Build.md
```

## Boundary Rules

- The Kernel must not import code, config or runtime artifacts directly from
  sibling modules.
- Cross-module work must happen through owner-local contracts and adapters.
- MCP tools are not Kernel functions unless their full behavior matches the
  Semantic Kernel SPEC.
- The Client Frontend owns UI rendering and dialogs; the Kernel owns the
  interaction contract and mirrored events.
- The MCP Server owns `stdio` transport; the Kernel owns workflow semantics.
- The Corpus Builder owns database persistence primitives; the Kernel owns when
  and why those primitives are called.
- `reset_database` is Agent-facing through Kernel/UI target collection:
  the Kernel collects Artifact Tree, Corpus DB name and destructive
  confirmation, then delegates the actual content reset to Corpus Builder
  `reset_active_corpus_db`. The owner must prove the active Semantic Release
  was preserved and that materialized content is empty after reset. Completed
  reset runs emit an `explain_now` final notice and expose the owner
  compaction and idle WAL-sidecar cleanup proofs so a logically empty SQLite DB
  is not mistaken for a still-filled database only because file artifacts had
  not yet been reduced.
- Additive database merge execution uses the Corpus Builder
  `multi_source_merge_databases` owner action with `mode=additive`; the owner
  derives semantic-only versus SQL+artifact behavior from the selected source
  states, and mixed empty/filled selections are valid when every source has a
  complete release proof. Filled merge artifact copying is also owner-side:
  DB-backed document artifacts and additional source `Documents/` / `Error
  Cases/` files are copied additively into the target Artifact Tree, while
  target-control roots such as `Corpus`, the newly materialized `Semantic
  Release` and active `Input` are not overwritten by source trees.
- The Kernel must not call LLM provider SDKs or read API/OAuth credentials.
  Provider calls go Kernel -> Orchestrator `kernel_llm_generate` -> Interpreter
  `generate_llm`, with Orchestrator-injected ephemeral runtime credentials.
  The Kernel uses the Orchestrator profile's model and `max_output_tokens`
  verbatim.
- Repairable LLM seed-output drift is normalized inside the Kernel before a
  validation retry is spent. Raw provider output stays in the LLM artifacts;
  downstream workflow state only consumes the canonicalized Kernel contract.
- Projection-authoring LLM calls receive the complete resolved taxonomy from
  the relevant `release.json`, not a sample-trimmed vocabulary. The Kernel
  exposes that taxonomy through the governed authoring-view contract and keeps
  flat allowed-code proof in `taxonomy_ref` for update-state validation.
- Strict provider output schemas keep the stable public facade in
  `semantic_control_kernel/workflows/llm_calls/output_schemas.py`. The schema
  DSL, payload-context extraction, shared semantic shapes, analysis builders
  and taxonomy/projection builders live in adjacent `llm_calls` modules so the
  Kernel owns the provider contract without turning it into a hidden schema
  monolith.
- Provider failures keep the owner error message in LLM artifacts and final
  blockers so real transport failures do not masquerade as validation errors.
- Long-running LLM calls emit `kernel.progress_event.v1` rows with
  `event_type=llm_step` when the call starts and when it completes or fails.
  These rows are visible to the Pipeline Manager progress surface but do not
  count as completed Kernel workflow steps for resume reconstruction.
- MCP Client Frontend interaction submits use auto-continuation: short
  target-collection handoffs stay inline, while long post-dialog continuations
  run in a Kernel background process after a visible
  `kernel_background_continuation` progress row is persisted. The
  background child closes inherited handles, so the single-threaded stdio MCP
  server can keep serving progress polls while LLM calls are active. The
  continuation progress row keeps `current_state_summary=unknown` because it is
  transport state, not Semantic Release workflow state.
- A background continuation must append a terminal
  `kernel_background_continuation` progress row after
  `continue_workflow_after_interaction` returns. Semantic `workflow_completed`,
  `workflow_failed` or `workflow_cancelled` mirrors remain the governed final
  notices, but the transport progress chain must also close so the Client
  Frontend cannot keep a completed run visible as running.
- Each background continuation writes a `*.ref.json` process reference under
  `state/debug/background_continuations/<workflow_run_id>/`. `kernel_cancel_active_run`
  and Client-Frontend Kernel reset use these refs to terminate the owned
  process tree before archiving active runtime state.
- Manual Pipeline runs mirror Orchestrator snapshot `stage_statuses` into
  `kernel.progress_event.v1.artifact_refs`. The Client Frontend can therefore
  render Intake, Optimizer, Interpreter, Validator, Normalizer, Corpus Builder
  and Embedding rows separately instead of truncating the whole subprocess
  state into one line.
- Permanent Agent-facing workflow tools start new workflow runs. They must not
  implicitly consume `state/resume/` entries from other unfinished work; resume
  requires explicit Kernel/UI resume state selection through
  `kernel_resume_state.resume_options[]` and
  `kernel_continue_resumable_workflow`.
- Resumed workflow final notices carry `kernel.workflow_explanation_context.v1`.
  Agents must explain `already_available` prerequisites separately from
  `performed_this_run` steps; reused Artifact Trees, databases or release
  artifacts must not be phrased as newly created by the continuation run.
- Client Frontend Agent context must be reconciled with fresh `kernel_status`
  before normal workflow selection. Stale mirrored dialogs or waiting progress
  from inactive workflow runs are historical context, not proof that a dialog is
  currently open.
- Active pending interaction request events are replayable through the
  Client Frontend event bridge until the interaction is submitted, cancelled,
  closed, expired or superseded. A browser cursor that moved past a pending
  dialog must not hide that Kernel-owned dialog.
- Historical open-dialog mirror events are not replayed as live dialogs unless
  the matching pending interaction is still active. If a browser cursor points
  past the end of the filtered event stream, the bridge returns the most recent
  visible event window instead of an empty progress surface.
- Client Frontend browser UX may show local dialog-submit pending state and a
  local workflow handoff progress row before real Kernel progress arrives. These
  states are UI-only, disable repeat submits, and must be replaced by real
  Kernel events or active workflow snapshots as soon as they are available.

## Truth Map

- Authoring truth for workflow semantics:
  `../Semantic Kernel SPEC/*.md`
- Authoring truth for this build sequence:
  `SPEC_Semantic_Control_Kernel_Build.md`
- Kernel-owned mutable runtime truth:
  `state/workflow_runs/`, `state/resume/`, `state/locks/`,
  `state/pending_confirmations/`, `state/pending_interactions/`,
  `state/receipts/`, `state/events/`, `state/attach_states/`,
  `state/artifact_trees/`, `state/bindings/`, `state/support/` and
  `state/quarantine/`
- Compiled truth:
  future generated registries or schemas, if introduced by a later phase
- Compatibility artifacts:
  temporary MCP legacy bridges during migration, if introduced by a later phase

No generated registry, cache, receipt or support bundle may become a second
editable workflow truth.

Phase 7 local Agent surface contracts are implementation contracts only:

- `agent_tool_definition.v1`
- `agent_tool_surface_inventory.v1`
- `agent_tool_invocation.v1`
- `agent_tool_result.v1`

They describe the model-visible inventory and invocation shell; they do not add
new workflow state truth and do not replace Phase 2 Kernel data contracts.

`state/bindings/` is the authoring truth only for the relation between a
database and an Artifact Tree. It does not own Corpus database content,
Artifact Tree files, document originals, Semantic Release package content or
Pipeline batch output.

Owner-module evidence that the Kernel may read but must not copy as editable
Kernel truth:

- Corpus database content and records: Corpus Builder / database owner.
- Artifact Tree folders and documents: Artifact Tree / Pipeline owner modules.
- Semantic Release package content: Semantic Release artifact owner / Corpus
  Builder activation contract.
- Active runtime release pointer: Corpus Builder / Pipeline activation owner.
- MCP transport/support state: `07 - MCP Server`.
- Browser, credential and dialog state: `Client Frontend`.

## Runtime and State

The module uses a local CPython 3.11 runtime under `runtime/python/` and must
not require Host Python or a global shared runtime for normal operation.

- Build the runtime from the module root with `build-runtime.bat`.
- Check the runtime from the module root with `check-runtime.bat`.
- Product runtime dependencies for Phase 1: none.
- `runtime/runtime-manifest.json` is source documentation.
- `runtime/python/` is generated runtime payload, not source truth.

Mutable state must stay under the Phase 3 repository layout below. Tests use
explicit temporary state roots and must not write to production `state/`.
`StatePaths.ensure_layout()` creates this repository-owned baseline. Raw owner
adapter calls are persisted under `state/adapter_calls/`; redacted per-workflow
diagnostics remain under `state/debug/adapter_calls/`.

```text
state/
|- README.md
|- state_root_manifest.json
|- .tmp/
|- .fs_locks/
|- workflow_runs/
|  |- active/
|  |- history/
|- resume/
|- pending_confirmations/
|  |- active/
|  |- history/
|- pending_interactions/
|  |- active/
|  |- history/
|- locks/
|  |- active/
|  |- history/
|- receipts/
|  |- confirmations/
|  |- operations/
|  |- recoveries/
|  |- index/
|     |- by_workflow/
|     |- by_target/
|- events/
|  |- progress/
|  |- mirror/
|  |- recovery/
|  |- tool_availability/
|- attach_states/
|  |- by_database/
|  |- history/
|- artifact_trees/
|  |- active/
|  |- history/
|- bindings/
|  |- records/
|  |- index/
|  |  |- by_database_path/
|  |  |- by_artifact_root/
|  |- history/
|- adapter_calls/
|- debug/
|  |- traces/
|  |- adapter_calls/
|  |- background_continuations/
|  |- llm_attempts/
|  |- redaction_reports/
|- support/
|  |- index.json
|  |- bundles/
|  |- cleanup_history/
|- archive/
|  |- resets/
|- quarantine/
   |- corrupt/
   |- partial_writes/
```

All repository state files are UTF-8 JSON, pretty printed with sorted keys and
a trailing newline. Stores write through `AtomicJsonStore`, use same-volume
temporary files under `state/.tmp/`, lock final paths through `state/.fs_locks/`
and validate by reading the final file back. Corrupt state is quarantined under
`state/quarantine/corrupt/<store_name>/` with a reason sidecar instead of being
silently overwritten.

Locks persist type-specific liveness evidence and conflict on the lock table's
target granularity. Expired locks remain blocking until recovery proves owner
liveness and writes the appropriate receipt.

Receipts under `state/receipts/` are immutable audit truth. Corrections are new
operation or recovery receipts; existing receipts are not edited.

Database-creation completion mirrors are governed final notices, not generic
chat summaries. They must include the created Artifact Tree path and Corpus
database path in both the visible summary and
`technical_detail_ref.workflow_completion.created_artifacts`; ready default
database completion also includes the default Semantic Release path.
The default-taxonomy/no-projections completion additionally includes
`projectionless_release_state_path`, taxonomy-present/projections-missing
flags and `database_ready_for_ingest: false`.
The custom-taxonomy/no-projections completion uses the same governed notice
shape, but exposes `custom_taxonomy_stage_path` instead of a projectionless
default-release state artifact. It reports taxonomy-present/projections-missing
flags, `database_ready_for_ingest: false`, and exactly one resume continuation
through `kernel_resume_state` / `kernel_continue_resumable_workflow` to
`create_custom_projection_path`.
Database-creation routes without a specialized final-notice payload still emit
a compact governed fallback with `agent_explanation_guidance.response_mode =
"explain_now"` and `technical_detail_ref.workflow_completion` or
`technical_detail_ref.workflow_blocked`, so the Client Frontend can surface the
final notice in chat. Completion fallback summaries must state that the run is
finished, include performed Kernel steps through `workflow_explanation_context`,
and forbid stale waiting-dialog claims.
When a database-creation path is continued through Kernel resume, the mirror
also includes `workflow_explanation_context`; visible wording must distinguish
previously available creation prerequisites from release/projection work done by
the current run.

Manual Pipeline Manager ingestion uses the same governed interaction shape:
`manual_pipeline_run` accepts no model-visible paths, opens Artifact Tree
selection, resolves the Corpus DB, reads the active Semantic Release, scans
`Input` and asks the user to confirm the files before calling internal
`pipeline_run`. If Error Cases exist, the Kernel may first offer to restore
those sources from proven Kernel evidence even when `Input` already contains
new files; a rejected restore continues with the existing `Input` files and
does not reopen the restore dialog. If `Input` is empty, previous batch
originals may also be restored from a valid final manifest. The route then
returns to normal Input confirmation before ingestion. The owner call sends the
confirmed `input_files` list to the Orchestrator, which constrains Kernel-owned
runs to those content hashes instead of silently retrying hidden
`pipeline_state.json` Error Case records. While the Orchestrator runs, snapshot
changes are mirrored as `kernel.progress_event.v1` rows; Error Case progress
counts only recoverable source files under `Error Cases/**/originals/**`, and
the final notice reports materialized documents and Error Cases.

Database-merge completion mirrors are governed final notices as well. Successful
Kernel-internal empty and filled merge routes emit
`agent_explanation_guidance.response_mode = "explain_now"` with
`technical_detail_ref.workflow_completion` under the `database_merge` family.
The completion payload includes `merge_run_id`, `merge_route`, source count,
target Artifact Tree path, target database path, collision manifest evidence,
the merged release path and, for filled merges, the merge ID-map fingerprint
plus copied Artifact Tree file count.
The Pipeline Manager entry now uses governed source/target collection:
`database_merge_additive_only` keeps an empty model-visible schema, opens
`choose_merge_database_count`, then source Artifact Tree path fields through
`choose_databases_to_merge`, then `choose_new_artifact_root_folder`, then
`choose_merge_projection_mode`, and resumes through
`continue_workflow_after_interaction`. The Kernel derives source
descriptors from the selected live Artifact Trees. Active bindings and
Kernel-held attach state may enrich known sources, but they are not required
for merge source entry: the resolver validates each selected Artifact Tree,
finds exactly one Corpus DB, reads the complete Semantic Release package in
that tree and assigns an import-local source ID when no durable owner ID exists.
If a tree contains a default release plus exactly one non-default release, the
non-default release is selected; otherwise the newest complete release package
is selected. Source and target paths are never accepted from chat. A source DB
that contains only active-release metadata such as `semantic_snapshots` remains
empty for merge routing; filled classification requires document, payload,
evidence, embedding or materialization-audit content.
`choose_merge_projection_mode` persists `preserve_source_projections` or
`merge_to_single_projection` in the merge selection. Single-projection merge is
accepted only for all-empty sources; filled routes block before owner preflight
or target mutation with a user-visible notice.
During merge finalization the Normalizer may return the compiled custom
Semantic Release identity nested under `release_ref` with top-level
`semantic_release_id` and `semantic_release_version` aliases. The Kernel
unwraps that nested `release_ref` as the canonical proof before
`write_semantic_release`, attach and activation, and still requires
`release_id`, `release_version` and `release_fingerprint`.
Merged custom releases are written through Normalizer
`materialize_semantic_release_candidate`, not through the default
`publish_semantic_release` path. A merge-context `release_ref` already carries
the merged taxonomy/projection refs, so `base_release_path` and
`projection_update_state` are not required for that detached custom write.
The resulting `custom_release_path` is the concrete bundle file
`Semantic Release/releases/<release_id>/release.json`. Package directories are
layout internals only; attach-state persistence, activation preflight,
activation and merge completion mirrors use the `.json` bundle path accepted by
Corpus Builder. Detached custom merge bundles persist top-level
`release_fingerprint` as an alias of the canonical content `fingerprint` so
later rebuild-from-artifacts can prove the release identity directly from the
bundle file. Merge finalization does not run the Corpus Builder
`load_semantic_release` status probe before activation; the written bundle is
held in Kernel attach state, and Corpus Builder validates the release/database
pair at `activation_preflight` and `activate_semantic_release`.
After `write_semantic_release`, the Kernel refreshes the release identity from
the owner write output. Activation proof uses the fingerprint of the written
`release.json` bundle, so a pre-write candidate fingerprint from
`create_custom_semantic_release` cannot block activation as stale identity.
Merge final notices may arrive in the same event poll as the background
continuation transport progress. The terminal mirror proves workflow outcome,
and the terminal background progress row closes the transport marker.
Client Frontend recovery chrome treats only recovery options or event-scoped
recovery tools as recovery state; permanent next-step tools on a
`workflow_completed` mirror must not render "Recovery required" and completion
retires stale recovery chrome from the active Pipeline Manager surface.
Filled-route SQL backfill uses the closed Corpus Builder
`backfill_sql_from_merge_artifacts` owner action. Its target proof carries both
`database_path_hash` and `target_database_path_hash` inside `target_identity`
and owner proof; `target_database_path_hash` is not a standalone top-level
owner request field.
When the filled route copies already-materialized documents, source
`projection_json` payload headers may still name the source taxonomy line.
Corpus Builder treats this as an initial target-activation condition, not as an
already-active foreign-line mutation: projection IDs must still exist in the
merged release, and the first activation aligns payload headers to the merged
release before the target DB becomes runtime-active.

`empty_database_default_taxonomy_no_projections` persists its taxonomy-only
truth as
`Semantic Release/staged/taxonomy/default_taxonomy_without_projections/projectionless_release_state.json`
with schema `kernel.default_taxonomy_projectionless_release_state.v1`. The
temporary default attach pointer is archived and cleared after projection
stripping; continuation is governed through `kernel_resume_state` and
`kernel_continue_resumable_workflow`, not implicit primary-tool reuse.
`empty_database_custom_taxonomy_no_projections` instead persists the staged
custom taxonomy ref plus `Semantic Release/incomplete_semantic_release.json`.
When `create_custom_taxonomy_path` is selected from a `no_semantic_release`
resume option, the Kernel reuses the existing Artifact Tree and empty Corpus DB,
stages the taxonomy, writes the incomplete marker/resume context, and exposes
`create_custom_projection_path` as the only valid next authoring step.
Custom taxonomy staging passes the full
`kernel.create_taxonomy_update_state.input.v1` payload to Normalizer. The staged
`taxonomy.json` stores that full `update_state`; the staged component identity
is only the taxonomy ID/fingerprint proof. Resume and projection authoring
rehydrate taxonomy codes, fallbacks and sectioned taxonomy core from
`source_analysis_refs` instead of treating the identity wrapper as the whole
taxonomy.
Direct Agent calls to database-creation continuation routes block with
`continuation_requires_resume_option` and create no workflow, recovery event or
event-scoped tool availability; they must be entered through
`kernel_resume_state` and `kernel_continue_resumable_workflow`.

Default-release attach and activation are target-scoped Corpus Builder calls.
The Kernel passes `write_global_mirrors=false` for these owner calls so the
target database receives its activation snapshot without rewriting
`05 - Corpus Builder` module-global Published/Active/Report mirrors.

`state/bindings/` may author a database-to-Artifact-Tree relation only after the
target database path exists and the matching active Artifact Tree ref is present.
It still does not own database bytes or Artifact Tree files.

`KernelStateResetService.reset_runtime_state()` archives active runtime state
into `state/archive/resets/<reset_id>/`. It clears active workflow/runtime
surfaces plus active database bindings and Kernel-held attach pointers:
`events/recovery/`, `events/tool_availability/`, `bindings/records/`,
`bindings/index/by_database_path/`, `bindings/index/by_artifact_root/` and
`attach_states/by_database/`. It preserves receipts, binding history,
attach-state history, support refs, progress/mirror event history and
quarantine evidence. The Client Frontend event bridge treats the newest reset
manifest timestamp as a visibility boundary, so pre-reset terminal progress,
mirror and event-scoped recovery tool availability are not replayed as active
state. It
never deletes Corpus databases, Artifact Tree folders, Semantic Release
packages, document originals, Pipeline batch artifacts, MCP Server state or
Client Frontend state.

## Operations And Support

Phase 18 observability adds local debug evidence and hardened support bundles
without changing workflow truth ownership. This README and
`SPEC_Semantic_Control_Kernel_Build.md` remain the implementation authority for
operations behavior. `../Semantic Kernel SPEC/` remains referenced workflow
intent subject to the Spec Drift Control Rule.

### Runtime State Locations

- Runtime truth stays under `state/workflow_runs/`, `state/resume/`,
  `state/locks/`, `state/receipts/`, `state/events/`, `state/attach_states/`,
  `state/artifact_trees/` and `state/bindings/`.
- Raw adapter-call request/response/result evidence lives under
  `state/adapter_calls/` through `StatePaths.adapter_calls_dir`.
- Phase 18 debug evidence lives under `state/debug/traces/`,
  `state/debug/adapter_calls/`, `state/debug/background_continuations/`,
  `state/debug/llm_attempts/` and `state/debug/redaction_reports/`.
- Immutable support bundles live under `state/support/bundles/` with the
  support index at `state/support/index.json` and cleanup history at
  `state/support/cleanup_history/`.

### Trace And Progress Correlation

- `workflow_run_id` and progress `sequence_index` remain the UI correlation
  keys.
- Local Client Frontend handoff/pending rows are not correlation records and do
  not replace `kernel.progress_event.v1`.
- `TraceLinkStore` adds local debug-only correlation across workflow runs,
  progress events, mirror events, adapter diagnostics, LLM attempt diagnostics
  and support bundles.
- Trace links are derived debug evidence. They do not replace receipts, resume
  state, locks or owner artifacts.

### Support Bundle Inspection

- Every Phase 18 support bundle contains
  `support_bundle_manifest.json`, `safe_summary.md`, `included_refs.json`,
  `trace_links.json` and `redaction_report.json`.
- Open support bundles through the Kernel support surface or read the files
  locally from `state/support/bundles/<support_bundle_id>/`.
- `kernel_open_support_bundle` returns a safe summary plus refs only. It does
  not dump raw bundle contents into chat.

### Redaction Guarantees

- Support bundles, adapter diagnostics and LLM diagnostics use the shared
  `support_safe_v1` redaction profile by default.
- Secrets, bearer tokens, OAuth-like tokens, raw prompt text, raw provider
  output, raw stack traces, full database payloads and unredacted external
  absolute paths must not appear in user-visible summaries or Agent mirrors.
- External absolute paths are hashed into stable `[path:<hash>]` placeholders
  unless a state-relative or artifact-relative ref is already safe to show.

### Common Blockers And Recovery Evidence

- `final_llm_validation_failure` keeps failed-attempt refs and diagnostics but
  does not ask the Agent or user to repair JSON in chat.
- `support_only_unrecoverable` remains a typed terminal recovery state with a
  safe support bundle and no invented recovery steps.
- `missing_capability` adapter diagnostics are support evidence only until
  Phase 19 provides the owner capability.

### Sample Evidence For Custom Creation

- `select_sample_files` is the creation-time user interaction for sample-based
  taxonomy/projection authoring. It asks the user to place raw sample documents
  in the active Artifact Tree `Input` folder and confirm presence.
- Raw samples are not sent directly to `analyze_samples`. The Kernel calls the
  existing Orchestrator/Optimizer sample-inspection action, reads optimizer
  `.raw` artifacts, and normalizes them into `kernel.analyze_sample.input.v1`.
  Duplicate page/aggregate OCR blocks are deduplicated before prompting.
- The owner-boundary payload for sample inspection declares
  `action=inspect_source_document_sample` and runs with the long-running adapter
  timeout because PDF/OCR sample inspection can exceed the ordinary read-only
  boundary.
- Orchestrator owns the Optimizer OCR runtime. Its sample-inspection action
  injects the configured `optimizer_ocr` model and credentials into the
  Optimizer debug session; the Kernel only consumes returned raw refs.
- If owner sample inspection fails, for example because the Optimizer OCR model
  is missing, the Kernel surfaces that owner diagnostic as the blocker instead
  of reporting the sample as merely unselected.
- After the user confirms `select_sample_files`, the Client Frontend bridge
  continues the database-creation workflow from persisted progress events so
  already completed Artifact Tree, database and release-preparation steps are
  reused instead of re-executed.
- Prebuilt `kernel.analyze_sample.input.v1` JSON under `Input` remains accepted
  for tests and resume state, but the production path is raw sample file ->
  optimizer raw -> Kernel analyzer input -> LLM.

### Custom Semantic Release Writes

- Default release writes still call Normalizer `publish_semantic_release`,
  which exports the saved Normalizer source package.
- A custom taxonomy by itself is not written or attached as a complete Semantic
  Release. Taxonomy-only creation remains `semantic_release_incomplete` until
  custom projections are created, validated, written, attached and activated as
  a complete custom release.
- Custom projection creation writes detached candidates through Normalizer
  `materialize_semantic_release_candidate`. The Kernel passes the unwrapped
  custom `release_ref`, the default base release path and
  `kernel.create_projections_update_state.input.v1`; Normalizer writes the full
  custom `release.json` with `projection_catalog` and
  `runtime_semantic_assets`. Kernel-owned detached custom releases also persist
  top-level `release_fingerprint` equal to `fingerprint`; historical bundles
  that only expose `fingerprint` remain accepted through adapter aliases.
- Custom projection identities are derived from
  `projection_precursors[].projection_id`. The old Phase 19 scaffold fallback
  `projection_phase19` is not a valid runtime default for custom projection
  creation.
- The Kernel updates `custom_release_ref` from the written release output before
  attach and activation, so downstream target-identity proof uses the final
  materialized release fingerprint, not the earlier candidate placeholder.
- Report-text LLM calls remain Markdown contracts. The validator tolerates a
  single JSON wrapper such as `{"report": "<markdown>"}` by unwrapping it before
  validation; other JSON output remains invalid.

### Runtime Check And Test Commands

- `build-runtime.bat`
- `check-runtime.bat`
- `dev-tests\\run-tests.bat tests\\test_phase18_support_bundle_schema.py`
- `dev-tests\\run-tests.bat tests\\test_phase18_support_bundle_redaction.py`
- `dev-tests\\run-tests.bat tests\\test_phase18_trace_correlation.py`
- `dev-tests\\run-tests.bat tests\\test_phase18_adapter_diagnostics.py`
- `dev-tests\\run-tests.bat tests\\test_phase18_llm_failure_bundle.py`
- `dev-tests\\run-tests.bat tests\\test_phase18_retention_policy.py`
- `dev-tests\\run-tests.bat tests\\test_phase18_logs_are_not_truth.py`
- `dev-tests\\run-tests.bat tests\\test_phase18_operations_readme.py`

### Cleanup And Retention

- Support bundle retention is metadata-first. Bundles are not deleted
  automatically by product workflow code.
- `SupportBundleRetentionPolicy.plan_prune(...)` is dry-run-first.
- `SupportBundleRetentionPolicy.apply_prune(...)` may delete only expired
  bundles and must write cleanup history under `state/support/cleanup_history/`.
- Receipt files, workflow run records, recovery receipts and owner artifacts are
  never prune targets.

### Logs Are Not Workflow Truth

- Logs, trace links, adapter diagnostics and support bundles may explain what
  happened.
- They must not be used to reconstruct missing receipts, infer target identity,
  re-create recovery options or decide whether a destructive operation is safe.
- If canonical receipt, lock, binding or resume evidence is missing, the Kernel
  must block through typed recovery instead of treating debug evidence as
  substitute truth.

## Deviation Log

| Rule | Deviation | Reason | Follow-up |
| --- | --- | --- | --- |
| Runtime must be locally built and checkable | None for Phase 1 runtime shell | Runtime build/check wrappers and runtime preflight are implemented | Keep runtime preflight green in later phases |
| Product workflow actions must be implemented and tested | Manifest still uses the `agent_surface_shell` label, but the permanent Agent-facing tools now dispatch current Phase 9 through Phase 19 handlers instead of the old `workflow_not_implemented` placeholder shell | The public tool names and empty model-visible schema stayed phase-stable while later phases replaced the handlers behind them | Keep the surface contract stable unless spec `23` changes in the same change |
| Phase 12 merge interaction collection | `database_merge_additive_only` starts with an empty Agent payload, opens governed source-count, source Artifact Tree path and target-root dialogs, resumes through `continue_workflow_after_interaction`, and completed merge routes emit `explain_now` final notices | Source descriptors are derived from selected live Artifact Trees; active binding/attach state can enrich known sources but missing binding state does not block a provable source tree | Keep the interaction-port regression green and do not add model-visible merge path arguments |
| Phase 12 rebuild interaction collection | `database_rebuild_from_artifacts` starts with an empty Agent payload, opens governed existing Artifact Tree and database-name dialogs, opens destructive `user_confirmation` only after the exact target path and loaded release fingerprint are known, and completed rebuild routes emit `explain_now` final notices | The target DB path, Semantic Release identity and overwrite receipt are Kernel-derived; the Agent never authors rebuild paths, names or overwrite decisions. The Corpus Builder owner call receives only `action=rebuild_from_artifacts`, `pipeline_root`, target `corpus_db_path` and the loaded `release_path`, then proves DB, Artifact Root and release fingerprint. | Keep rebuild interaction and receipt regressions green and do not add model-visible rebuild path arguments |
| SHOULD keep files near 200 LOC | `semantic_control_kernel/orchestrator_contract.py` and `semantic_control_kernel/bootstrap/runtime_report.py` remain above the guidance as path-stable surface/bootstrap wrappers | Splitting these entrypoint wrappers during the Phase 1 regression audit would make contract paths harder to reason about; tests now stage-map them as surface/bootstrap preflight files and protect their import boundaries | Revisit only with a path-stable wrapper split in a dedicated refactor |
| SHOULD keep files near 200 LOC | Phase 5 `domain/state_machine/resolver.py`, `evaluator.py` and `models.py` remain above the guidance as a split but dense state-machine domain surface | The Phase 5 crash-prevention audit tightened confirmation, evidence and resolver invariants with targeted edits; splitting the public domain surface during that repair would risk path drift across later workflow phases | Revisit in a dedicated path-stable state-machine refactor after transition/evidence/confirmation regression coverage remains green |
| SHOULD keep files near 200 LOC | Phase 6 `services/kernel_mirror_event_service.py`, `surface/client_frontend_bridge.py` and `dev-tests/tests/test_phase6_frontend_event_sink.py` remain above the guidance as path-stable mirror, host-bridge and regression surfaces | The Phase 6 crash-prevention audit repaired option mirroring and expired interaction relay with targeted edits; splitting during the repair would risk MCP/Client Frontend bridge path drift. Stage map: mirror request mapping and event-scoped recovery exposure; bridge event polling, response/cancel relay, event-scoped tool definitions and persisted event collectors; regression tests cover sink, polling, cancellation and receipt behavior. | Revisit in a dedicated path-stable Phase 6 bridge/mirror refactor after Phase 6, Phase 7 and Phase 13 recovery visibility tests remain green |
| SHOULD keep files near 200 LOC | Phase 13 `surface/recovery_tools.py`, `domain/recovery/semantic_exception_handler.py`, `services/agent_tool_workflow_dispatch.py`, `validation/recovery_validation.py` and `mcp_contract.py` remain above the guidance as path-stable recovery, dispatch, validation and MCP contract surfaces | The Phase 13 crash-prevention audit repaired target-identity lock binding, event supersession and blocked-workflow recovery bridging with targeted edits; splitting these public contract paths during the repair would risk recovery-tool, MCP and Agent dispatch drift. Stage map: recovery tool authorization and output shaping; semantic exception classification/persistence/mirror emission; permanent workflow dispatch to recovery bridge; recovery contract validation; MCP contract routing and event-scoped service wiring. | Revisit in a dedicated path-stable Phase 13 surface split only after Phase 13 and adjacent MCP event-scoped recovery tests remain green |
| Dev tests must be runnable and meaningful | Phase 7 tests now prove the permanent tool surface reaches live handlers or real workflow-specific blockers under isolated Kernel state roots | Placeholder shells and generic starter rejections are false-green risks once later phases exist | Keep representative Phase 9, 10, 11 and 12 dispatch coverage green alongside the phase-local inventory tests |
| Semantic Kernel SPEC omits Phase 3 repository-local mechanics | `drift_preflight: build_plan_authority_applied` | Build plan resolves exact state layout, local schemas, atomic writes, lock TTLs, receipt immutability, reset behavior and fixture roots | Keep Phase 3 repository tests green and treat later workflow persistence as repository-only |
| Semantic Kernel SPEC omits Phase 7 local Agent shell contracts | `drift_preflight: build_plan_authority_applied` | Build plan resolves local Agent tool definition, inventory, invocation and result contracts plus the no-domain-value rule | Treat Phase 7 inventory as the source for MCP and Client Frontend integration phases |
| Phase 20 release readiness is stricter than code presence | None | Go-live depends on the full regression matrix, cleanup scans, prior-phase evidence and a written readiness decision, not on workflow code existing in the tree | Re-run the full go-live matrix before any live cutover |

## Phase 19 Owner Capability Boundary

- Phase 19 unblocks five former Pipeline capability gaps through owner-local contracts:
  - Artifact Tree Contract Hardening
  - Database Analysis Evidence Reader
  - Semantic Release Domain Service
  - Pipeline Batch Manifest And Batch/Reingest Domain Service
  - Multi-Source Merge Domain Service
- The Kernel still owns workflow routing, target selection, confirmations, recovery policy, continuation scope and Agent-visible tool policy.
- Owner modules now return typed owner envelopes and evidence refs; adapters translate those envelopes into Kernel receipts and workflow-local diagnostics.
- No Phase 19 adapter reaches back into the retired MCP-hosted Kernel implementation or the old action-catalog path.
