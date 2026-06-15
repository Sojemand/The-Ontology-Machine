# Database Creation Workflows

> Split from SPEC_Semantic_Runtime_Kernel_New.md.
> Source path: C:\Users\Norma\Workspace\The Ontology Machine\SPEC_Semantic_Runtime_Kernel_New.md.
> Source lines: 248-432.

Database creation workflows for default and custom semantic releases.

---

Database creation Functions

Normal Agent dispatch rule for all primary database-creation functions:
	- A fresh user request starts the selected workflow from the first user action.
	- Stale Client Frontend mirror history, old waiting dialogs or unrelated resumable work must not replace the required `choose_artifact_root_folder`, `name_artifact_root_folder` and `name_database` sequence unless the user explicitly chooses a Kernel resume path.
	- Explicit resume uses `kernel_resume_state.resume_options[]` followed by `kernel_continue_resumable_workflow` with the exact opaque `resume_option_ref`. The Agent must not call a primary `empty_database_*` tool to continue an existing database-creation run.
	- The Client Frontend must provide visible pending/progress feedback from the Agent handoff through each required Kernel-owned user interaction. Dialog submissions disable repeat input immediately; local pending rows are UI-only until real Kernel progress or active workflow state arrives.
	- Resumed workflows must expose `kernel.workflow_explanation_context.v1` in the final notice. The Agent must distinguish `already_available` preconditions from `performed_this_run`; it must not describe reused Artifact Trees, databases or release artifacts as newly created in the continuation run.

empty_database_no_semantic_release
	- creates an empty Database with no semantic release attached

		User actions required
			- choose_artifact_root_folder
			- name_artifact_root_folder
			- name_database

		Kernel actions required
			- create_standard_artifact_folder_tree
			- create_empty_database within the corpus folder

	- Final State: One empty Database blocked due to missing semantic release
		- Final notice uses the shared database-creation payload shape, requests Agent explanation with `explain_now`, and exposes the created Artifact Tree path and Corpus database path in both visible summary text and `technical_detail_ref.workflow_completion.created_artifacts`.
		- Follow-up options toward default release or custom taxonomy/projection are explicit `kernel.resume_option.v1` selections returned by `kernel_resume_state`. A new normal Agent call to another database-creation primary tool must start a new workflow and must not silently consume this resume state.

		- Required next steps:
			- write_semantic_release into the Artifact semantic release folder
			- attach_default_semantic_release_to_database
			or:
			- create_custom_taxonomy
			- stage_custom_taxonomy_for_semantic_release
			- create_custom_projection_path
			- validate_projections_against_taxonomy
			- stage_custom_projections_for_semantic_release
			- create_custom_semantic_release
			- write_semantic_release into the Artifact semantic release folder
			- attach_custom_semantic_release_to_database
			then:
			- activate_semantic_release
		- Final State: One Database with an activated semantic release


empty_database_default_taxonomy_no_projections
	- Creates an empty Database with default taxonomy staged from the default semantic release, but no projections

		User actions required
			- choose_artifact_root_folder
			- name_artifact_root_folder
			- name_database

		Kernel actions required
			- create_standard_artifact_folder_tree
			- create_empty_database within the corpus folder
			- export_default_semantic_release from the Normalizer default blueprint into the target Artifact Tree Semantic Release area
			- write_semantic_release into the Artifact semantic release folder
			- attach_default_semantic_release_to_database
			- remove_projection_from_database

	- Final State: One Database with a blocked semantic release due to missing projections
		- `dc_remove_default_projections` must consume the Normalizer owner `updated_release_ref` after every projection removal and the final ref must contain the default taxonomy with `projection_refs: []`.
		- The Kernel persists `Semantic Release/staged/taxonomy/default_taxonomy_without_projections/projectionless_release_state.json` as `kernel.default_taxonomy_projectionless_release_state.v1`.
		- `staged_taxonomy_ref`, `projectionless_release_ref`, `projectionless_release_state_ref` and `incomplete_semantic_release.json` point to this projectionless state.
		- The temporary default attach pointer is archived/cleared after projection stripping. Attach receipts and attach-state history remain audit evidence.
		- Final notice uses the shared database-creation payload shape, requests Agent explanation with `explain_now`, exposes created paths including `projectionless_release_state_path`, marks taxonomy present/projections missing, and says the database is not ready for ingest. If this path is reached through resume, the notice separates existing prerequisites from newly performed release/projection-stripping work.
		- The only completion continuation is explicit Kernel resume toward `create_custom_projection_path`: `kernel_resume_state` returns the option and `kernel_continue_resumable_workflow` executes the selected opaque resume option.
		- If projection removal blocks, the final notice reports blocker code/summary plus progress through DB creation, default export/write, attach and projection removal.

		- Required next steps:
			- create_custom_projection_path for active Database
				- Required: Existing Taxonomy within active Database
			- validate_projections_against_taxonomy
			- stage_custom_projections_for_semantic_release
			- create_custom_semantic_release
			- write_semantic_release into the Artifact semantic release folder
			- attach_custom_semantic_release_to_database
			- activate_semantic_release
		- Final State: One Database with an activated semantic release


empty_database_default_taxonomy_default_projections
	- Creates an empty Database with the complete default semantic release attached

		User actions required
			- choose_artifact_root_folder
			- name_artifact_root_folder
			- name_database

		Kernel actions required
			- create_standard_artifact_folder_tree
			- create_empty_database within the corpus folder
			- export_default_semantic_release from the Normalizer default blueprint into the target Artifact Tree Semantic Release area
			- write_semantic_release into the Artifact semantic release folder
			- attach_default_semantic_release_to_database
				- includes Corpus Builder load/preflight proof before Kernel attach-state persistence
			- activation_preflight immediately before owner activation
			- activate_semantic_release

	- Final State: One functioning Database with an active semantic release
		- Final notice uses the shared database-creation payload shape, marks the semantic release active, requests Agent explanation with `explain_now`, and exposes Artifact Tree, Corpus database and default Semantic Release paths. Frozen compatibility mirrors may still carry historical next-action labels; live dispatch authority comes from the current 16-tool surface.
		- On explicit continuation from `no_semantic_release`, the final notice must say the Artifact Tree and empty Corpus DB were reused/already available and that this run exported, wrote, attached and activated the default Semantic Release.
		- If blocked, the final notice must include which of database creation, default release export/write, attach and activation already happened.


empty_database_default_taxonomy_custom_projections
	- Creates an empty Database with the default taxonomy and custom projections

		User actions required
			- choose_artifact_root_folder
			- name_artifact_root_folder
			- name_database
			- select_sample_files

		Kernel actions required
			- create_standard_artifact_folder_tree
			- create_empty_database within the corpus folder
			- export_default_semantic_release from the Normalizer default blueprint into the target Artifact Tree Semantic Release area
			- write_semantic_release into the Artifact semantic release folder
			- attach_default_semantic_release_to_database
			- remove_projection_from_database
			- create_custom_projection_path
				- Required: Existing Taxonomy within active Database
				- select_sample_files confirms raw samples in the artifact tree Input folder
				- inspect raw samples through the Orchestrator/Optimizer sample path and normalize optimizer `.raw` outputs into `kernel.analyze_sample.input.v1`
				- analyze_samples through the route-normalized sample evidence
				- create_projections_to_sample_analyses
				- create_projections_update_state
				- create_custom_projection
				- validate_projections_against_taxonomy

			- stage_custom_projections_for_semantic_release
			- create_custom_semantic_release
			- write_semantic_release into the Artifact semantic release folder
			- attach_custom_semantic_release_to_database
			- activate_semantic_release

	- Final State: One Database with an activated semantic release



empty_database_custom_taxonomy_no_projections
	- Creates an empty Database with a custom Taxonomy staged for a later semantic release

		User actions required
			- choose_artifact_root_folder
			- name_artifact_root_folder
			- name_database
			- select_sample_files

		Kernel actions required
			- create_standard_artifact_folder_tree
			- create_empty_database within the corpus folder
			- create_custom_taxonomy_path
				- select_sample_files confirms raw samples in the artifact tree Input folder
				- inspect raw samples through the Orchestrator/Optimizer sample path and normalize optimizer `.raw` outputs into `kernel.analyze_sample.input.v1`
				- analyze_samples through the route-normalized sample evidence
				- create_taxonomy_to_sample_analyses
				- create_taxonomy_update_state
				- create_custom_taxonomy

			- stage_custom_taxonomy_for_semantic_release
			- write_semantic_release into the Artifact semantic release folder

	- Final State: One Database with a blocked semantic release due to missing projections

		- Required next steps:
			- create_custom_projection_path
			- validate_projections_against_taxonomy
			- stage_custom_projections_for_semantic_release
			- create_custom_semantic_release
			- write_semantic_release into the Artifact semantic release folder
			- attach_custom_semantic_release_to_database
			- activate_semantic_release
		- Final State: One Database with an activated semantic release


empty_database_custom_taxonomy_custom_projections
	- Creates an empty Database with custom Taxonomy and custom projections as a complete custom semantic release

		User actions required

			- choose_artifact_root_folder
			- name_artifact_root_folder
			- name_database
			- select_sample_files

		Kernel actions required

			- create_standard_artifact_folder_tree
			- create_empty_database within the corpus folder
			- create_custom_taxonomy_path
				- select_sample_files confirms raw samples in the artifact tree Input folder
				- inspect raw samples through the Orchestrator/Optimizer sample path and normalize optimizer `.raw` outputs into `kernel.analyze_sample.input.v1`
				- analyze_samples through the route-normalized sample evidence
				- create_taxonomy_to_sample_analyses
				- create_taxonomy_update_state
				- create_custom_taxonomy
			- stage_custom_taxonomy_for_semantic_release

			- create_custom_projection_path
				- Required: staged custom taxonomy
				- reuse confirmed sample evidence from select_sample_files when present, otherwise request sample confirmation for projection authoring
				- inspect raw samples through the Orchestrator/Optimizer sample path and normalize optimizer `.raw` outputs into `kernel.analyze_sample.input.v1`
				- analyze_samples through the route-normalized sample evidence
				- create_projections_to_sample_analyses
				- create_projections_update_state
				- create_custom_projection
				- validate_projections_against_taxonomy

			- stage_custom_projections_for_semantic_release
			- create_custom_semantic_release
			- write_semantic_release into the Artifact semantic release folder
			- attach_custom_semantic_release_to_database
			- activate_semantic_release

	- Final State: One Database with an activated semantic release
