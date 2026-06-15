# User Function Surface

> Split from SPEC_Semantic_Runtime_Kernel_New.md.
> Source path: C:\Users\Norma\Workspace\The Ontology Machine\SPEC_Semantic_Runtime_Kernel_New.md.
> Source lines: 797-944.

User selection, proceed, security, and confirmation function surface.

---

Functions Definitions

User select Functions:
	- Selection through a popup window/file/folder selector

choose_artifact_root_folder
name_artifact_root_folder
	- name_ and choose_ can be combined into a single windows folder picker with "create folder" capability.
	- gets passed into:
		- create_standard_artifact_folder_tree

name_database
	- a separate small dialogue window
	- gets passed into
		- create_empty_database
		- database_rebuild_from_artifacts

select_sample_files
	- Opens a popup dialogue that points the user to the active Artifact Tree `Input` folder.
	- The user places raw sample documents (`.pdf`, `.txt`, `.doc`, `.docx`, images, markdown or other supported Optimizer inputs) into `Input` and confirms with a "samples present" decision.
	- The Kernel then uses the existing Orchestrator/Optimizer sample inspection path to produce optimizer `.raw` artifacts and normalizes them into `kernel.analyze_sample.input.v1` before `analyze_samples`.
	- No raw sample document is sent directly to the sample-analysis LLM call.
	- gets passed into:
		- create_custom_taxonomy_path
		- create_custom_projection_path

use_current_active_database
	- uses the database that is already active at workflow start
	- gets passed into
		- manual_pipeline_run

use_custom_database_path
	- a folder picker
	- the selected database becomes active_database for the workflow
	- gets passed into
		- manual_pipeline_run

choose_merge_database_count
	- a Kernel-owned text input dialog that asks how many source databases will be merged.
	- accepts only a user-entered integer of 2 or more through the Client Frontend interaction response.
	- does not accept Agent chat arguments and is used only to size the following source Artifact Tree path dialog.
	- gets passed into:
		- choose_databases_to_merge

choose_databases_to_merge
	- a dialogue window with one source Artifact Tree path field per count returned by `choose_merge_database_count`.
	- recursive search resolves each selected Artifact Tree folder to exactly one live Corpus database path and one complete live Semantic Release package; active bindings may enrich known sources but are not required.
	- mixed empty/filled selections are valid; all-empty routes semantic-only and any-filled routes to filled additive merge with empty sources contributing zero SQL/artifact rows.
	- must assign or read a stable `source_database_id` for every selected source database before collision classification.
	- source paths are Client Frontend interaction values, never Agent chat arguments.
	- gets passed into:
		- database_merge_additive_only, which selects the Kernel-internal empty or filled merge route after source classification

choose_new_artifact_root_folder
	- windows folder picker with "create folder" capability.
	- gets passed into:
		- choose_merge_projection_mode

choose_merge_projection_mode
	- a Kernel-owned choice dialog for database merge output policy.
	- choices:
		- `preserve_source_projections`: keep source projections side by side in the target release.
		- `merge_to_single_projection`: compile source projections into one target projection.
	- `merge_to_single_projection` is valid only when all selected source databases are empty; filled routes block with a user-visible notice before target mutation.
	- gets passed into:
		- database_merge_additive_only, which continues through the Kernel-selected internal merge route

User Security Functions:
	- Confirmation through a popup window

user_confirmation (with added corresponding explanation)
	- is run by:
		- manual_pipeline_run
		- reset_database
		- database_merge_additive_only and its Kernel-internal merge routes
		- reconcile_merged_semantic_release
		- reconcile_merged_database
		- database_rebuild_from_artifacts
	- works as a proceed block until user confirms possible outcomes

Confirmation And Receipt Rules
	- Confirmation requests are Kernel objects, not Pipeline actions.
	- A confirmation request must include:
		- the function or route that is asking for confirmation;
		- the exact target identity;
		- the current Kernel state snapshot identity;
		- a user-readable explanation of the possible outcome;
		- whether the action is destructive, overwrite-capable, additive-only or long-running;
		- the confirmation scope.
	- A confirmation receipt is valid only for the exact target identity it was created for.
	- A destructive function must re-resolve target state after confirmation and before mutation.
	- Long-running MCP workflows must be able to return pending_confirmation and later resume with the receipt.
	- Pipeline adapters may require their own confirmation artifacts. Those artifacts are implementation details generated from Kernel receipts and do not replace Kernel confirmation.

Kernel Locks
	- Locks are Kernel safety objects that protect workflow state from concurrent or unsafe mutation.
	- Locks must be acquired before the Pipeline adapter call that mutates the locked target.
	- Locks must be released or marked failed when the workflow finishes, aborts or moves into a resumable pending state.
	- Required lock types:
		- active-run lock;
		- workspace lock;
		- database lock;
		- release attach/activation lock;
		- merge lock;
		- rebuild overwrite lock.
	- Release attach/activation locks block activation when another run is writing to the same target database.

Resumable User Interaction
	- User interaction may be provided through a GUI popup, an MCP pending request, a CLI prompt or another host surface.
	- The user interaction surface is not allowed to decide Kernel workflow state directly.
	- The user interaction surface returns selection values, confirmation receipts or cancellation signals.
	- The Kernel resumes the workflow only after validating the returned value against the current state and target identity.
	- Expired pending interactions must be recoverable by reopening the Kernel-owned dialog from WorkflowResumeStore when target identity still matches.
	- If target identity no longer matches, the Kernel must block and emit recovery_options instead of accepting stale user input.

Recovery User Interaction Surface
	- Recovery dialogs are Kernel-owned user interactions.
	- Recovery dialogs may be opened directly by the Kernel or reopened through an event-scoped recovery tool exposed in a Kernel auto-call mirror event.
	- Recovery dialogs are not Agent chat questions.
	- The Agent must not collect recovery values in chat as a replacement for these dialogs.
	- Recovery dialog requests must include:
		- recovery_id;
		- workflow_run_id when a workflow exists;
		- target identity;
		- current Kernel state snapshot identity;
		- user-visible cause;
		- recovery effect;
		- risk_class;
		- allowed choices or required selector;
		- expiration policy.
	- Recovery dialog responses must return:
		- recovery_id;
		- selected value or cancellation signal;
		- target identity;
		- state snapshot identity;
		- host surface identity.
	- recovery_id is echoed on every recovery dialog response and becomes the
	  selected value only for `partial_pipeline_run_recovery_dialog`.
	- `support_bundle_dialog` may omit a mutation value and use optional
	  `confirmation_decision` only as a close acknowledgement.
	- The Kernel must validate recovery dialog responses before resuming or mutating state.

Recovery Dialog Types
	- path_reselection_dialog
		- used for invalid database paths, invalid Artifact Tree paths, moved folders and missing target paths.
		- may reopen use_custom_database_path, choose_artifact_root_folder or choose_new_artifact_root_folder.
	- missing_input_dialog
		- used when source files, sample files or reingest files are missing.
		- points the user to the correct Input or reingest location and waits for user confirmation through the host surface.
	- overwrite_decision_dialog
		- used when a target database, target folder or rebuild output already exists.
		- returns overwrite confirmation or alternate target selection.
	- merge_reconciliation_dialog
		- used when merge collisions require a semantic, SQL, artifact or duplicate policy decision.
		- must preserve collision manifest identity.
	- stale_lock_dialog
		- used only when the Kernel cannot resolve a possibly stale lock without user-visible risk.
		- offers keep waiting, inspect status, cancel active workflow or request stale-lock recovery when allowed.
	- rebind_database_artifact_tree_dialog
		- used when a database and Artifact Tree need explicit user selection before DatabaseArtifactRebindService can validate a binding.
		- must not allow arbitrary binding without Kernel validation.
	- discard_or_archive_staged_work_dialog
		- used when the user intentionally abandons staged work.
		- requires confirmation that explains what will be archived, discarded, preserved and not touched.
	- partial_pipeline_run_recovery_dialog
		- used when a Pipeline run partially wrote outputs and the Kernel cannot automatically finalize or quarantine without user-visible choice.
		- offers only Kernel-provided recovery options.
	- support_bundle_dialog
		- used to expose a safe support/debug summary and references for final errors or unrecoverable states.
		- must not paste raw stack traces, secrets or full raw LLM responses into chat.

Kernel Auto-Call And User Surface
	- A Kernel auto-call mirror event may announce that a recovery dialog is available.
	- The auto-call may temporarily expose `kernel_open_recovery_dialog` or another event-scoped recovery tool to the Agent only when the mirror also carries Kernel-authored recovery_options binding that tool.
	- The auto-call is a Kernel message, not a user message.
	- The Kernel must expire event-scoped recovery tool availability when the recovery dialog is resolved, cancelled, expired or superseded; the Client Frontend must then remove those tools from the model-visible surface.

KernelUserInteractionService And ClientFrontendEventSink
	- KernelUserInteractionService builds and validates Kernel-owned user selection, proceed and confirmation requests.
	- ClientFrontendEventSink exposes those requests to the available host surface; Phase 6 provides an in-memory fake sink and later frontend phases provide HTTP/browser rendering.
	- returns only selected values, confirmation receipts or cancellation signals.
	- does not call Pipeline adapters.
	- does not decide Kernel workflow state.
	- must preserve the request ID and target identity when returning confirmation receipts.
	- opens and reopens Kernel-owned recovery dialogs.
	- returns recovery dialog responses only to the Kernel recovery service that created the request.
	- must preserve recovery_id, target identity and state snapshot identity for recovery dialog responses.
