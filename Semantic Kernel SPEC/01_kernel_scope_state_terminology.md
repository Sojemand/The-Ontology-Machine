# Kernel Scope, State, And Terminology

> Split from SPEC_Semantic_Runtime_Kernel_New.md.
> Source path: C:\Users\Norma\Workspace\The Ontology Machine\SPEC_Semantic_Runtime_Kernel_New.md.
> Source lines: 1-83.

Kernel consistency scope, semantic release state model, and shared terminology.

---

Workable Pipeline Manager tool boundaries.

Kernel consistency scope
	- This document describes the Semantic Runtime Kernel in isolation.
	- Integration boundaries with Orchestrator, Normalizer, Corpus Builder, the MCP Server and the Agent-facing Pipeline Manager surface are defined by the corresponding component specs in this folder.
	- The goal of this revision is internal consistency: complete and incomplete semantic release states must be explicit, workflows must not activate incomplete releases, and Kernel paths must not pretend to attach single taxonomy or projection artifacts directly to a database.
	- Prompt structures, JSON schemas, workflow states and Pipeline boundary contracts are specified by this component spec set. Intentional gaps must be marked as missing_or_mismatched in the relevant boundary spec, not left as placeholders.
	- Semantic release ID/version/fingerprint assignment remains owned by the Normalizer/Corpus Builder boundary when a semantic release object is created or rebuilt. activate_semantic_release only makes an already attached and written release runtime-active.
	- pipeline_run must persist semantic release provenance at batch and record level. Changing the active semantic release affects future pipeline runs only; already materialized records remain explainable by the release, taxonomy and projection fingerprints with which they were created.

Kernel state model
	- no_semantic_release
		- Database exists but has no semantic release attached.
		- pipeline_run is blocked.
	- semantic_release_incomplete
		- Taxonomy or projections are missing.
		- The incomplete taxonomy/projection artifacts may be staged in the Artifact Tree Semantic Release folder for later use.
		- pipeline_run and activate_semantic_release are blocked.
	- semantic_release_complete_not_active
		- A semantic release contains one taxonomy and at least one projection, but has not been activated yet.
	- semantic_release_active
		- A complete semantic release is attached and activated for the active database.
		- pipeline_run may write into the active database.

Kernel terminology
	- default_semantic_release
		- A complete pre-existing semantic release.
		- It does not need to be created by a custom workflow and can be attached to a database, written into the Artifact Tree and activated directly.
	- taxonomy
		- The classification foundation from which projections are derived.
	- projection
		- One thematic projection derived from the taxonomy.
		- If the taxonomy is small enough, one projection may cover the whole taxonomy.
	- projections
		- The list of projections in a semantic release.
		- The list may contain exactly one projection or multiple projections.
	- active_database
		- The database selected at the beginning of a workflow.
		- If a custom database path is selected, that database becomes the active database for the workflow.
		- pipeline_run always writes into the active_database.
	- active semantic release
		- The semantic release pointer currently used for new pipeline_run execution.
		- Activating a new semantic release does not rewrite already materialized database records.
	- materialized semantic release
		- The semantic release provenance stored on a pipeline batch and resolvable for every materialized database record.
		- It may differ from the currently active semantic release after later release updates.
	- pipeline_batch_id
		- Stable ID for one pipeline_run materialization batch.
		- Used to group records, artifacts and cleanup/re-ingest operations.
	- semantic materialization ref
		- The minimal provenance reference that connects a materialized record to its pipeline_batch_id, semantic release, taxonomy fingerprint and projection fingerprint.
	- staging taxonomy or projections
		- Single taxonomy or projection artifacts are not attached directly to a database.
		- They are staged in the Semantic Release folder until create_custom_semantic_release combines one taxonomy and at least one validated projection into a complete semantic release.
	- Stage
		- Persists individual taxonomy or projection artifacts in the Artifact Tree Semantic Release folder.
		- Does not create a complete semantic release object.
		- Does not attach anything to a database.
		- Does not make anything runtime-active.
	- Create Semantic Release
		- Builds one complete semantic release object from one validated taxonomy and at least one validated projection.
		- May use staged artifacts as input.
		- Does not attach the release to a database.
		- Does not write the release unless write_semantic_release is called.
		- Does not activate the release.
	- Build Updated Semantic Release
		- Computes a new semantic release object from an existing attached release plus a validated taxonomy, projection or merge update result.
		- Does not write the release artifact.
		- Does not attach or activate the release.
	- Attach
		- Sets the selected database's semantic release pointer to a release ID, version, fingerprint or local release path.
		- Does not make the release runtime-active.
		- Leaves the database in semantic_release_complete_not_active when the attached release is complete.
	- Write
		- Persists semantic release artifacts into the Artifact Tree Semantic Release folder.
		- Does not compute release content.
		- Does not attach the release to a database.
		- Does not activate the release.
	- Activate
		- Makes the attached complete semantic release runtime-effective for the active_database.
		- Enables pipeline_run.
		- Is blocked for missing, detached or incomplete semantic releases.
