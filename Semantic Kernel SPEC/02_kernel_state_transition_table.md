# Kernel State Transition Table

> Split from SPEC_Semantic_Runtime_Kernel_New.md.
> Source path: C:\Users\Norma\Workspace\The Ontology Machine\SPEC_Semantic_Runtime_Kernel_New.md.
> Source lines: 84-144.

Canonical operational state table for Kernel actions and routes.

---

Kernel State Transition Table
	- This table is the canonical operational state table for the active_database.
	- If a workflow checklist and this table disagree, this table wins and the workflow checklist must be corrected.
	- `Post-State` describes the active_database semantic release state unless the row explicitly says that only a detached artifact is produced.
	- `unchanged` means the active_database semantic release state does not change, even if artifacts, reports or SQL rows are written.
	- LLM supplemented functions do not directly mutate active_database state. They write validated artifacts or update-state JSON that later Kernel-only functions consume.

Semantic Exception Handling
	- The Kernel state table is the canonical source for semantic exception handling.
	- Semantic exception handling converts blocked, unsafe, partial, invalid or failed workflow states into typed recovery states.
	- A typed recovery state is not an unhandled crash.
	- A typed recovery state must define:
		- how it is detected;
		- what it blocks;
		- which Kernel recovery mechanism may handle it;
		- what may be written or mutated;
		- what the post-state can be;
		- what must never happen during recovery.
	- Recovery states must preserve target identity, receipts, locks and resume state before any recovery mutation.
	- Recovery options are Kernel-authored and may be mirrored to the Agent only through event-scoped auto-call mirror events.

Kernel State Resolution
	- Every row in this table is evaluated against a typed Kernel state snapshot before the function or route is allowed to run.
	- The Kernel State Resolver is the canonical reader for active_database state.
	- The Kernel State Resolver must resolve:
		- active artifact tree identity;
		- active artifact tree path;
		- active database path;
		- database emptiness: empty or filled;
		- database semantic release state:
			- no_semantic_release;
			- semantic_release_incomplete;
			- semantic_release_complete_not_active;
			- semantic_release_active;
		- attached semantic release identity;
		- active semantic release identity;
		- semantic release revision, version, fingerprint, runtime locale and materialization identity when available;
		- active run lock;
		- active or pending confirmation receipts;
		- whether a user-selected database path is allowed to become active_database.
	- The Kernel State Resolver may read Pipeline module state as evidence, but Pipeline module state is not canonical until it has been converted into a Kernel state snapshot.
	- `inspect_active_corpus`, module-local Corpus Builder context and Orchestrator UI state are read primitives only. They must not become canonical state truth.
	- The Kernel State Resolver returns `kernel.active_database_state.v1`, blocking reasons when state cannot be resolved, and exact target identities for dangerous operations.

Attach And Activate State
	- The table keeps written semantic release artifacts, attached semantic release pointers and active semantic release runtime state as separate states.
	- `write_semantic_release` writes release artifacts only.
	- `attach_semantic_release_to_database` records a complete release pointer and leaves the database in semantic_release_complete_not_active.
	- `activate_semantic_release` makes the attached release runtime-effective and leaves the database in semantic_release_active.
	- If the Pipeline can persist a non-active attached release pointer, the Kernel may use that persistence through its SemanticReleaseAdapter.
	- If the Pipeline only persists active snapshots or active releases, the Kernel must persist semantic_release_complete_not_active in Kernel state until activation.
	- `activate_semantic_release` must prove that the release being activated is exactly the release attached by the Kernel.
	- Activation blocks if the attached release pointer is missing, the written release artifact changed after attach, the target database changed after attach, the active Pipeline snapshot does not match the attached release identity, or an active Pipeline run is in progress for the target database.

| Function / Route | Required State | Required Artifacts / Inputs | Writes / Mutates | Post-State | Blocks If | User Confirmation |
|---|---|---|---|---|---|---|
| create_standard_artifact_folder_tree | no active artifact tree for target path | chosen artifact root folder, artifact root name | Standard Artifact Tree folders | unchanged | invalid_target_path, target_conflict | no |
| create_empty_database | artifact tree exists | database name, Corpus folder | empty database in Corpus folder | no_semantic_release | missing_artifact_tree, target_conflict, binding_conflict | no |
| attach_semantic_release_to_database | no_semantic_release or semantic_release_incomplete or semantic_release_complete_not_active or semantic_release_active | written complete semantic release object or path | database semantic release pointer | semantic_release_complete_not_active | release_missing, release_incomplete, release_not_written, release_fingerprint_mismatch, database_missing | no |
| attach_default_semantic_release_to_database | no_semantic_release or semantic_release_incomplete | written complete default_semantic_release object or path | database semantic release pointer through attach_semantic_release_to_database | semantic_release_complete_not_active | release_missing, release_incomplete, release_not_written, database_missing | no |
| attach_custom_semantic_release_to_database | no_semantic_release or semantic_release_incomplete | written complete custom semantic release object or path | database semantic release pointer through attach_semantic_release_to_database | semantic_release_complete_not_active | release_missing, release_incomplete, release_not_written, database_missing | no |
| write_semantic_release | semantic_release_incomplete or semantic_release_complete_not_active or semantic_release_active or detached release context | complete semantic release object or intentionally staged incomplete release artifacts | Artifact Tree Semantic Release folder artifacts | unchanged | release_missing, missing_artifact_tree, release_fingerprint_mismatch | no |
| activate_semantic_release | semantic_release_complete_not_active | attached complete semantic release pointer and written release artifact | runtime-active semantic release marker / database metadata | semantic_release_active | attach_pointer_missing, release_incomplete, release_not_written, projection_taxonomy_invalid, active_run_lock_conflict, release_fingerprint_mismatch | no |
| remove_projection_from_database | semantic_release_complete_not_active | attached complete default release with default projections | taxonomy-only staged default release evidence for creation workflow | semantic_release_incomplete | attach_pointer_missing, release_missing, projection_taxonomy_invalid, pipeline_capability_missing | no |
| stage_custom_taxonomy_for_semantic_release | no_semantic_release or semantic_release_incomplete | validated custom taxonomy or `kernel.create_taxonomy_update_state.input.v1` | staged taxonomy in Semantic Release folder | semantic_release_incomplete | update_state_invalid, release_fingerprint_mismatch, active_run_lock_conflict, pipeline_capability_missing | no |
| stage_custom_projections_for_semantic_release | no_semantic_release or semantic_release_incomplete | validated projections or `kernel.create_projections_update_state.input.v1`, staged or active taxonomy | staged projections in Semantic Release folder | semantic_release_incomplete | update_state_invalid, release_missing, projection_taxonomy_invalid, pipeline_capability_missing | no |
| create_custom_semantic_release | semantic_release_incomplete or detached staging context or merge finalization context | one staged, attached or reconciled taxonomy and at least one staged, attached or reconciled validated projection | complete custom semantic release artifact | detached artifact produced; active_database becomes semantic_release_complete_not_active only after write_semantic_release and attach_custom_semantic_release_to_database | release_missing, projection_taxonomy_invalid, merge_collision_unresolved, pipeline_capability_missing | no |
| create_custom_taxonomy | no direct state mutation | `kernel.create_taxonomy_update_state.input.v1` | custom taxonomy artifact | unchanged until staged or attached through release workflow | update_state_invalid, pipeline_capability_missing | no |
| create_custom_projection | no direct state mutation | `kernel.create_projections_update_state.input.v1`, valid taxonomy ref | custom projection artifacts | unchanged until staged or attached through release workflow | update_state_invalid, projection_taxonomy_invalid, pipeline_capability_missing | no |
| validate_projections_against_taxonomy | semantic_release_incomplete or semantic_release_complete_not_active or semantic_release_active | taxonomy and one or more projections | validation result or blocker | unchanged | projection_taxonomy_invalid | no |
| pipeline_run | semantic_release_active | input files present in active artifact tree Input folder | database records with semantic materialization refs, Documents artifacts, `kernel.pipeline_batch_manifest.v1` | semantic_release_active | release_missing, release_incomplete, confirmation_missing, input_missing, materialization_provenance_missing, active_run_lock_conflict | yes |
| reset_database | any active_database state | active database, artifact tree, semantic release preservation policy | clears SQL/database content while preserving artifact tree and semantic release | same semantic release state as before reset | database_missing, release_fingerprint_mismatch, binding_conflict | yes |
| empty_databases_merge_path | selected source databases are all empty | selected databases, selected or new artifact root, semantic releases, merge collision policy | target artifact tree, empty target database, additive semantic release merge, merge collision manifest, reconciled semantic release | semantic_release_active | database_emptiness_unknown, release_missing, merge_collision_unresolved, binding_conflict | yes |
| filled_databases_merge_path | at least one selected source database is filled; empty sources may be present | selected databases, artifact trees for filled contributors, semantic releases, merge collision policy | target artifact tree, merged database content with preserved materialization refs, merge id map, merge collision manifest, reconciled SQL/artifacts/semantic release | semantic_release_active | database_emptiness_unknown, missing_artifact_tree, merge_collision_unresolved, materialization_provenance_missing, merge_policy_missing | yes |
| merge_database_empty | merge route internal | all source databases empty | empty database merge result | unchanged until route writes target | database_not_empty | no |
| merge_database_filled_additive | merge route internal | at least one filled source, merge collision policy | additive database merge result, merge id map, database collision manifest; empty sources contribute no SQL/artifact rows | target SQL/artifacts written, release activation still pending | database_empty, database_emptiness_unknown, merge_collision_unresolved, merge_policy_missing | no |
| merge_taxonomy_and_projections_additive | merge route internal | source semantic releases, merge collision policy | additive taxonomy/projection merge package, semantic collision manifest | unchanged until semantic release is created or updated | release_missing, projection_taxonomy_invalid, merge_collision_unresolved | no |
| reconcile_merged_semantic_release | merge route target not yet active | additive semantic release merge result, semantic collision manifest | reconciled taxonomy/projection merge package, resolved semantic collision manifest | unchanged until create_custom_semantic_release, write and attach | merge_collision_unresolved | yes |
| reconcile_merged_database | merge route target not yet active | merged SQL data, merged artifact tree, merged semantic release, merge id map, database/artifact/semantic collision manifests | reconciled SQL/artifacts/taxonomy/projection merge package, resolved merge collision manifest | unchanged until create_custom_semantic_release, write and attach | merge_collision_unresolved, materialization_provenance_missing | yes |
| write_combined_database | no direct state mutation | compatibility label only | no separate second owner mutation; SQL is written by merge_database_filled_additive | unchanged | n/a | no |
| fill_artifact_folder_tree | no direct state mutation | compatibility label only | no separate owner call; artifacts are copied by merge_database_filled_additive | unchanged | n/a | no |
| backfill_sql | merge or rebuild route internal | artifact data and target database | missing SQL records or links where recoverable | unchanged | missing_artifact_tree, database_missing, materialization_provenance_missing | no |
| corpus_builder_load_semantic_release | rebuild route internal | Artifact Tree Semantic Release folder | loaded semantic release for Corpus Builder | unchanged | release_missing, release_incomplete, projection_taxonomy_invalid | no |
| run_corpus_builder | rebuild route internal | loaded semantic release, artifact tree data, target database path | rebuilt database | semantic_release_complete_not_active | release_incomplete, invalid_target_path, missing_artifact_tree | no |
| create_embeddings | rebuilt database exists | embedding API configured, database records | embedding records/indexes | unchanged | embedding_unavailable | no |
| database_rebuild_from_artifacts | selected Artifact Tree has intact semantic release | artifact tree, target database name, optional overwrite confirmation | rebuilt database, optional embeddings, activation | semantic_release_active | release_missing, release_incomplete, target_conflict, confirmation_missing, database_missing | yes if overwrite |

Recovery State Classes
	- Recovery state classes are Kernel-level blocker states, not Agent guesses.
	- A recovery state class must be emitted as a structured Kernel mirror event when it is user-visible or blocks the current conversation.
	- Structured recovery events, recovery options, recovery receipts and progress events use the contracts registered in `11_kernel_internal_data_contracts.md`.
	- Recovery state classes may expose event-scoped recovery tools through allowed_agent_tools.
	- Recovery state classes must not expose the full recovery tool list permanently.
	- Required recovery state classes:
		- stale_lock
		- target_identity_changed
		- broken_database_artifact_binding
		- semantic_release_incomplete_staged
		- partial_pipeline_run
		- unresolved_merge_collision
		- missing_manifest_or_originals
		- final_llm_validation_failure
		- expired_pending_interaction
		- support_only_unrecoverable

Recovery State Transition Table

| Recovery State | Detected By | Blocks | Allowed Recovery Mechanism | Writes / Mutates | Post-State | Must Not |
|---|---|---|---|---|---|---|
| stale_lock | KernelStateResolver or LockStore liveness check | workflows targeting the locked resource | StaleLockRecoveryService through event-scoped `kernel_resolve_stale_lock` or Kernel dialog | lock marked released, failed, active, or pending-resume; recovery receipt | lock state proven and workflow may resume or remain blocked | force-unlock live owners |
| target_identity_changed | KernelStateResolver, ConfirmationService, WorkflowResumeStore | pending confirmation, resume, destructive operation, activation, merge, cleanup | reopen Kernel dialog, inspect resume state, cancel workflow, or discard/archive staged work | no target mutation unless a confirmed recovery path runs | target reselected, workflow cancelled, or stale state archived | accept stale confirmation or stale path values |
| broken_database_artifact_binding | DatabaseArtifactBindingRegistry or KernelStateResolver | custom DB selection, pipeline_run, cleanup, merge, rebuild, analysis | DatabaseArtifactRebindService through event-scoped `kernel_rebind_database_artifact_tree` and recovery dialog | corrected binding receipt or support-only blocker | binding valid or operation remains blocked | guess binding from similar paths |
| semantic_release_incomplete_staged | KernelStateResolver or activation step | pipeline_run and activation | continue missing staged workflow, open recovery dialog, discard/archive staged work | may write/stage missing release parts only through valid workflow; may archive staged state | semantic_release_active, semantic_release_incomplete preserved, or staged work archived | silently activate incomplete release |
| partial_pipeline_run | PartialPipelineRunReconciler, ReceiptStore, batch manifest audit | cleanup, reingest, analysis, subsequent pipeline_run | event-scoped `kernel_reconcile_partial_pipeline_run`, recovery dialog, support bundle | finalize manifest/receipt, quarantine partial output, or create cleanup/reingest options | proven complete, quarantined, or blocked with support bundle | treat partial data as complete without proof |
| unresolved_merge_collision | merge collision manifest, reconcile_merged_semantic_release, reconcile_merged_database | merge finalization and activation | merge_reconciliation_dialog, cancel workflow, discard/archive merge target, support bundle | resolved collision manifest, archived target, or support bundle | merge may continue or target is safely abandoned | silently choose semantic collision policy |
| missing_manifest_or_originals | cleanup/reingest workflow, BatchManifest reader, Artifact Tree audit | remove/retrieve sample batch, retrieve originals, reingest | recovery dialog, support bundle, discard cleanup path, manual filesystem action if Kernel exposes it | restored manifest only if provable; otherwise support/recovery receipt | cleanup path continues or remains blocked | delete records when affected set cannot be isolated |
| final_llm_validation_failure | LLMFunctionAdapter after retry exhaustion | LLM-supplemented workflow step | event-scoped retry, cancel, inspect resume state, support bundle | no database mutation; failed attempts and support bundle persisted | workflow retried, cancelled, resumable, or support-only final error | consume invalid JSON or ask Agent/user to repair JSON |
| expired_pending_interaction | KernelUserInteractionService or WorkflowResumeStore | pending input/selection/confirmation | reopen recovery dialog when target identity matches; otherwise resume inspection or cancel | renewed pending interaction or cancelled/archived state | pending interaction active again or workflow blocked/cancelled | accept expired dialog response |
| support_only_unrecoverable | any Kernel recovery service | current workflow continuation | `kernel_open_support_bundle`, cancel/archive when available | support bundle and final error receipt | support-visible terminal state | invent recovery options |

Recovery Transition Rules
	- Recovery transitions must revalidate the current recovery event, mirror availability, recovery_id binding, target identity, state snapshot identity and service-specific proof before mutation. When the caller already has a fresh KernelStateResolver snapshot, recovery must use that snapshot rather than stale dialog/input payloads.
	- Recovery transitions must validate target identity against the mirror event, state snapshot and recovery_id.
	- Recovery transitions that mutate state must write an operation or recovery receipt.
	- Recovery transitions that require user choice must use KernelUserInteractionService recovery dialogs through the ClientFrontendEventSink host boundary.
	- Recovery transitions exposed to the Agent must be event-scoped, listed in allowed_agent_tools and bound to Kernel-authored recovery_options on the same mirror event.
	- A stale recovery_id must fail closed and emit a new Kernel mirror event.
