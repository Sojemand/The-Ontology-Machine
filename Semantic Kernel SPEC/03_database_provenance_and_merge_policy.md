# Database Provenance And Merge Policy

> Split from SPEC_Semantic_Runtime_Kernel_New.md.
> Source path: C:\Users\Norma\Workspace\The Ontology Machine\SPEC_Semantic_Runtime_Kernel_New.md.
> Source lines: 145-219.

Batch/record semantic materialization provenance plus database merge collision policy.

---

Database Materialization Provenance
	- The active semantic release is the release used for new pipeline_run execution. It is not a retroactive rewrite command.
	- Every pipeline_run must create one `kernel.pipeline_batch_manifest.v1` artifact and assign its `pipeline_batch_id` to all records and artifacts produced by that run.
	- The batch manifest must capture:
		- `pipeline_batch_id`
		- `semantic_release_id`
		- `semantic_release_version`
		- `release_fingerprint`
		- `taxonomy_id`
		- `taxonomy_version`
		- `taxonomy_fingerprint`
		- active projection refs with `projection_id` and `projection_fingerprint`
	- Every materialized document or normalized/projected record must be able to resolve:
		- `pipeline_batch_id`
		- `semantic_release_id`
		- `semantic_release_version`
		- `taxonomy_fingerprint`
		- `projection_id`
		- `projection_fingerprint`
	- `semantic_release_id` is the materialization field name. When a release package exposes the same value as `release_id`, it is copied into `semantic_release_id` for batch and record provenance.
	- Record-level storage may either denormalize these fields or store `pipeline_batch_id` plus a queryable join to the batch manifest, but `projection_id` and `projection_fingerprint` must remain queryable per materialized document or projection assignment.
	- If the active semantic release is updated after records already exist, old records keep their original materialization refs. New pipeline runs use the newly active release.
	- Backfill or re-ingest is optional and must create a new pipeline_batch_id with new materialization refs. It must not silently overwrite the provenance of earlier records.
	- Rebuild, merge and audit surfaces must distinguish the currently active semantic release from the releases under which existing records were materialized when those differ.
	- Filled-database additive updates extend the semantic release for future normalization. They do not by themselves re-normalize existing records.

Database Merge Collision Policy
	- `database_merge_additive_only` must classify collisions before any target database is activated.
	- The old user-facing idea of accepting "doubles" is implemented through explicit collision classes, not by blindly copying conflicting data.
	- Every merge route must write a `kernel.database_merge_collision_manifest.v1` artifact.
	- Filled merge routes must also write a `kernel.database_merge_id_map.v1` artifact for remapped SQL IDs, document IDs, artifact paths, batch IDs and embedding IDs.
	- Completed merge routes must surface the collision manifest evidence, and filled routes the merge ID-map evidence, in the governed `explain_now` final notice. The Agent may explain that evidence but must not author collision or source-selection decisions.
	- Semantic collisions are resolved by `reconcile_merged_semantic_release` for empty merges and by `reconcile_merged_database` for filled merges.
	- SQL, artifact, batch and embedding collisions are resolved deterministically when the policy defines a safe remap. They require user confirmation when the policy exposes a semantic choice.
	- Required collision classes:

| Collision Class | Default Policy | Resolution Owner | Blocks Activation If |
|---|---|---|---|
| taxonomy_code_same_fingerprint | merge one canonical code | merge_taxonomy_and_projections_additive | canonical fingerprints cannot be verified |
| taxonomy_code_different_meaning | requires_reconcile | reconcile_merged_semantic_release or reconcile_merged_database | user has not chosen rename, merge or mapping |
| taxonomy_code_same_label_different_code | keep both unless user maps | reconcile_merged_semantic_release or reconcile_merged_database | relationship ambiguity remains |
| projection_id_same_fingerprint | merge one canonical projection | merge_taxonomy_and_projections_additive | projection fingerprints cannot be verified |
| projection_id_different_fingerprint | requires_reconcile | reconcile_merged_semantic_release or reconcile_merged_database | user has not chosen rename, merge or mapping |
| projection_include_conflict | requires_reconcile | reconcile_merged_semantic_release or reconcile_merged_database | included taxonomy codes are unresolved |
| document_content_hash_duplicate | keep both by default; optional user choice may collapse duplicates | reconcile_merged_database | selected collapse cannot preserve source refs and provenance |
| same_original_hash_different_file_name | keep one content identity with filename aliases or keep both records by user choice | reconcile_merged_database | user choice missing where collapse changes record count |
| same_file_name_different_hash | rename with source database prefix | merge_database_filled_additive | target path cannot be made unique |
| document_id_collision | remap target document IDs | merge_database_filled_additive | ID map cannot preserve source_database_id and source_document_id |
| sql_primary_key_collision | remap target SQL IDs | merge_database_filled_additive | ID map incomplete or foreign keys cannot be rewired |
| artifact_path_collision | rename with source database prefix and source record suffix | merge_database_filled_additive | renamed path would still collide or source artifact missing |
| pipeline_batch_id_collision | namespace every colliding source batch with source database ID | merge_database_filled_additive | batch provenance cannot be preserved |
| embedding_id_collision | remap vector/embedding IDs to target IDs | merge_database_filled_additive or create_embeddings | embedding cannot be linked to remapped target record |
| same_embedding_source_hash_different_embedding_model | keep separate embedding records by embedding model/config fingerprint | merge_database_filled_additive or create_embeddings | embedding config fingerprint missing |
| record_release_version_mixed | preserve original materialization refs | merge_database_filled_additive | old release refs cannot be queried after merge |

	- Required merge provenance fields:
		- `source_database_id`
		- `source_database_path`
		- `source_artifact_root`
		- `source_record_id`
		- `source_document_id`
		- `source_original_file_name`
		- `source_content_hash`
		- `source_artifact_path`
		- `source_pipeline_batch_id`
		- `source_embedding_id`
		- `target_record_id`
		- `target_document_id`
		- `target_artifact_path`
		- `target_pipeline_batch_id`
		- `target_embedding_id`
	- `source_database_id` must be stable for the merge run. If the source database has no durable ID, the Kernel assigns an import-local source ID and records it in the merge manifest.
	- Merge source selection is live Artifact Tree based. The Kernel may reuse an active binding-derived durable source ID, but it must not require existing binding/attach state and must not search historical binding folders when the selected Artifact Tree proves one Corpus DB and a complete Semantic Release package.
	- `source_*` values are audit provenance. `target_*` values are the executable IDs and paths after remap.
	- A filled merge may contain records materialized under several semantic release versions. The target database must preserve those per-record refs and may activate only the reconciled target semantic release for future pipeline runs.
	- Merge and rebuild audit evidence must be able to report mixed materialization history after a filled merge.
	- If the same `source_pipeline_batch_id` appears in more than one source database, every affected target batch ID uses `<source_database_id>.<source_pipeline_batch_id>`. A merge ID-map row whose `source_database_id` is not in the selected source set is invalid.
