# Pipeline, Merge, And Rebuild Workflows

> Split from SPEC_Semantic_Runtime_Kernel_New.md.
> Source path: C:\Users\Norma\Workspace\The Ontology Machine\SPEC_Semantic_Runtime_Kernel_New.md.
> Source lines: 686-796.

Manual pipeline run, additive merge, and rebuild-from-artifacts workflows.

---

Shared resumable-final-notice rule:
	- Pipeline, merge and rebuild continuations must embed `kernel.workflow_explanation_context.v1` once they support resume/final notices.
	- Existing source databases, target folders, selected merge manifests, loaded Semantic Releases or rebuild manifests imported from resume state are `already_available`; only current-run ingestion, merge, write, attach or activation steps are `performed_this_run`.
	- Completed merge routes must emit a governed `kernel.mirror_event.v1` final notice with `agent_explanation_guidance.response_mode = "explain_now"` and `technical_detail_ref.workflow_completion`.
	- Merge completion detail must include `workflow_family = "database_merge"`, workflow tool, final state, `merge_run_id`, `merge_route`, source count/summary, target Artifact Tree path, target database path, collision manifest evidence, persistence outcome, safe next-step options and, for filled routes, merge ID-map evidence.
	- Completed and blocked rebuild routes must emit a governed `kernel.mirror_event.v1` final notice with `agent_explanation_guidance.response_mode = "explain_now"` and `workflow_family = "database_rebuild"`.

Pipeline run Functions

manual_pipeline_run
	- Runs ingestion directly on the active_database.

		User actions required
			- Choose Database options:
				- use_current_active_database
				- use_custom_database_path
			- Place source files into the active artifact tree Input folder
			- user_confirmation that input data is present

		Kernel-internal route actions required
			- verify active_database has semantic_release_active
			- pipeline_run
				- write data into active_database
				- produce or update the pipeline batch manifest

	- Final State: one active database with newly ingested data and a batch manifest available for cleanup/re-ingest workflows


database_merge_additive_only
	- Merges two or more Databases (filled or empty)
	- Mixed empty/filled merge is supported. If every source is empty the workflow runs semantic-only; if at least one source is filled it runs the filled additive SQL/artifact path, while empty sources contribute zero SQL/artifact records and still contribute their Semantic Release package.
	- Permanent Agent-facing calls do not accept selected source databases, target paths or merge policy as model-authored arguments. Source count, source Artifact Tree paths, target root and projection merge mode come from Kernel/UI state collected through `choose_merge_database_count`, `choose_databases_to_merge`, `choose_new_artifact_root_folder` and `choose_merge_projection_mode`, then validated against the selected live Artifact Trees before route classification.
	- `database_merge_additive_only` opens those interactions through `MergeInteractionPort` and resumes through `continue_workflow_after_interaction`; source descriptors are Kernel-derived, not user- or Agent-authored.
	- Active Kernel bindings and attach pointers may enrich known sources, but missing binding state does not block a source tree when the selected Artifact Tree itself proves one Corpus DB and a complete Semantic Release package. The resolver does not search historical state folders.
	- If a source Artifact Tree contains a default release plus exactly one non-default release, the non-default live release is selected. Otherwise the newest complete release package under `Semantic Release/releases/` is selected deterministically.
	- Each Kernel-built source descriptor carries `source_release_ref` with `taxonomy_ref` and `projection_refs`. If the live `release.json` stores only full `master_taxonomy` and `projections`, the Kernel derives the detached refs from those payloads and preserves the full projection payload for the merged release materialization.
	- Existing target roots require exact Kernel confirmation only when they contain contentful target data. Kernel-owned residue limited to `Documents/logs/merge_runs/<merge_run_id>/` selection, collision, or ID-map preview files from earlier blocked merge attempts is ignored for this conflict check.

		User actions required

			- choose_merge_database_count

			- choose_databases_to_merge (Artifact Tree path fields; recursive DB resolution):

			- choose_new_artifact_root_folder

			- choose_merge_projection_mode
				- `preserve_source_projections` keeps source projections side by side.
				- `merge_to_single_projection` compiles source projections into one target projection and is allowed only for all-empty source selections.

		Kernel actions required

			- empty_databases_merge_path
				- user_confirmation required with detailed outcome explanation when the target root already exists/non-empty or a semantic collision requires user choice
					- Collision Policy: taxonomy code collisions are classified by semantic fingerprint.
					- Collision Policy: projection ID collisions are classified by projection fingerprint.
					- Collision Policy: semantic collisions with different meanings require reconcile_merged_semantic_release before semantic release creation and activation.
					- reconcile_merged_semantic_release is mandatory before create_custom_semantic_release, write, attach and activate

				- create_standard_artifact_folder_tree
				- create_empty_database
				- merge_database_empty
					- validate that all source databases are empty
				- merge_taxonomy_and_projections_additive
					- use the complete `source_release_ref` values from the selected databases
					- produce a semantic merge package containing reconciled `taxonomy_ref` and `projection_refs`
					- when `projection_merge_mode = preserve_source_projections`, dedupe identical taxonomy/projection refs by identity and fingerprint, and classify same identity with different fingerprint as a semantic collision
					- when `projection_merge_mode = merge_to_single_projection`, deterministically compile source projections into one merged projection ref for the target release
				- reconcile_merged_semantic_release
					- user_confirmation required with change explanation
					- reconciliation receipts must reference the active merge manifest revision and carry selected_resolutions entries keyed by collision_id plus selected_resolution
				- create_custom_semantic_release
					- unwrap Normalizer nested `release_ref` as the canonical custom release proof; top-level `semantic_release_id` and `semantic_release_version` are aliases only
				- write_semantic_release within the semantic release folder
					- use detached custom release materialization for merge `release_ref`, not default release publishing
					- expose the written merged release as `Semantic Release/releases/<release_id>/release.json`; package directories are not valid attach/activation bundle paths
					- persist top-level `release_fingerprint` equal to the bundle `fingerprint`
					- refresh the activation `release_ref` from the write output; the written bundle fingerprint is canonical
				- attach_custom_semantic_release_to_database
				- activate_semantic_release
				- Final State:
					- one database with an activated semantic release
					- one empty artifact tree
					- final notice exposes `explain_now`, `merge_run_id`, `merge_route = empty_databases_merge_path`, target paths, collision manifest fingerprint, merged `release.json` path and safe next-step options

			- filled_databases_merge_path
				- User confirmation required with detailed outcome explanation when the target root already exists/non-empty or a collision requires user choice
					- Collision Policy: taxonomy and projection identity collisions require fingerprint comparison and reconciliation when meanings differ.
					- Collision Policy: SQL primary keys, document IDs, batch IDs, artifact paths and embedding IDs are remapped into the target namespace.
					- Collision Policy: duplicate document hashes are kept by default or collapsed only by explicit user choice.
					- Collision Policy: record-level semantic release provenance is preserved for all imported records.
					- reconcile_merged_database is mandatory before create_custom_semantic_release, write, attach and activate

				- create_standard_artifact_folder_tree
				- create_empty_database
				- merge_database_filled_additive
					- call Corpus Builder `multi_source_merge_databases` once with `mode=additive`
					- use all SQL/artifact data from filled source databases; skip empty sources for SQL/artifact rows

				- reconcile_merged_database
					- user_confirmation required with change explanation

				- backfill_sql if possible
				- create_custom_semantic_release
					- unwrap Normalizer nested `release_ref` as the canonical custom release proof; top-level `semantic_release_id` and `semantic_release_version` are aliases only
				- write_semantic_release within the semantic release folder
					- use detached custom release materialization for merge `release_ref`, not default release publishing
					- expose the written merged release as `Semantic Release/releases/<release_id>/release.json`; package directories are not valid attach/activation bundle paths
					- persist top-level `release_fingerprint` equal to the bundle `fingerprint`
					- refresh the activation `release_ref` from the write output; the written bundle fingerprint is canonical
				- attach_custom_semantic_release_to_database
				- activate_semantic_release
				- Final State:
					- one database with an activated semantic release
					- one artifact tree with all previous data
					- final notice exposes `explain_now`, `merge_run_id`, `merge_route = filled_databases_merge_path`, target paths, collision manifest fingerprint, merge ID-map fingerprint, merged `release.json` path and safe next-step options



database_rebuild_from_artifacts
	- Rebuilds a Database from Data within an existing Artifact Tree and intact semantic release
	- Permanent Agent-facing calls do not accept Artifact Tree paths, target database names or overwrite decisions as model-authored arguments. The Kernel collects the selected existing Artifact Tree through `choose_artifact_root_folder`, collects the DB name through `name_database`, and resumes through `continue_workflow_after_interaction`.

		User actions required

			- choose_artifact_root_folder from which the Database is rebuilt
			- name_database
			- if a database with the same name already exists in the artifact tree Corpus folder:
				- user_confirmation required to overwrite the existing database after the Kernel has resolved the exact target path and loaded Semantic Release fingerprint

		Kernel Actions required

			- overwrite confirmation required with change explanation only when the named target database already exists
				- confirmation receipt must be `kernel.confirmation_receipt.v1` scoped to artifact-root hash, target DB hash, loaded release fingerprint and workflow run ID
			- resolve target database path inside the selected artifact tree Corpus folder
			- block or request overwrite confirmation if the target database path already exists
			- corpus_builder_load_semantic_release from corresponding artifact folder
				- the Semantic Release folder is intact only when it contains at least one release package under Semantic Release/releases/<release_id>/release.json
			- run_corpus_builder on artifact tree data into the named target database
				- must prove the exact target database path and loaded Semantic Release fingerprint
				- Kernel adapter sends Corpus Builder `action=rebuild_from_artifacts`, `pipeline_root`, target `corpus_db_path` and the loaded Artifact-Tree `release_path`
				- Corpus Builder response must prove `database_path(_hash)`, `artifact_root_path(_hash)` and `release_fingerprint`
			- (if API configured) create_embeddings
			- attach_semantic_release_to_database
			- activate_semantic_release
			- Final State: one database with an activated semantic release
			- Final notice exposes `explain_now`, `rebuild_run_id`, artifact root, target database path, loaded release identity, rebuild manifest path, kernel persistence, overwrite receipt when applicable and safe next-step options
