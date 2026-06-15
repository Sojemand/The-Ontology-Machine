# Shared LLM Contract Rules

> Split from SPEC_Semantic_Runtime_Kernel_New.md.
> Source path: C:\Users\Norma\Workspace\The Ontology Machine\SPEC_Semantic_Runtime_Kernel_New.md.
> Source lines: 2369-2381.

Shared strict-output and validation rules for LLM supplemented Kernel functions.

---

Shared LLM Contract Rules
	- JSON examples use concrete values. Allowed enum values are listed in the surrounding rules and must not be encoded as pipe-delimited strings inside JSON values.
	- Compact Normalizer source paths used in `promotion_rules[*].source_paths` must start with one of:
		- `context.`
		- `content.fields.`
		- `content.rows[*].`
		- `content.structure.`
	- Source paths must be compact semantic paths, not raw artifact paths, page references, image references, SQL paths or file system paths.
	- Taxonomy creation proposals use `status: active` for generated terms because the Kernel is building a new taxonomy precursor.
	- Taxonomy and projection update proposals use `status: draft` for newly proposed additive terms or projections until the Kernel validates and promotes them.
	- Domains are represented as taxonomy codes in all LLM contracts. The Kernel may map those codes to the source package's internal domain IDs.
	- `domains` must include an `other` domain term where a full taxonomy proposal is created, but `fallback_codes` only contains document type, category, subcategory, field code, row type and cell code fallbacks.

OpenAI Strict Structured Output Rules
	- Structured Kernel LLM calls must attach an OpenAI-style `json_schema` response format with `strict: true` whenever the Kernel can build a schema that satisfies the strict subset.
	- Every Kernel LLM provider request uses `max_output_tokens: 20000`.
	- Report-generation calls `user_report_samples` and `user_report_database` are the only LLM calls in this group that do not attach a JSON schema. They use text output and report validation.
	- The provider schema is an output-shaping contract, not the final validator. The Kernel still parses and validates the returned object against the function-specific rules before downstream consumption.
	- Strict provider schemas must use:
		- a root object schema;
		- `additionalProperties: false` on every object;
		- `required` listing every declared property on every object;
		- nullable types such as `["string", "null"]` for fields that may not apply;
		- empty arrays `[]` for empty collections;
		- recursive strict compliance for array items, nested objects and `anyOf` variants.
	- Strict provider schemas must not depend on dynamic object keys or unresolved `$ref` references.
	- Dynamic marker maps in model output are represented as closed list entries:
		- `{"domain_id": "<taxonomy-domain-code>", "markers": ["..."]}`
	- `routing_lexicon.domain_markers`, `add_domain_markers` and `remove_domain_markers` therefore use arrays of domain marker entries in LLM output. The Kernel may normalize those arrays back to Normalizer-compatible maps after validation.
	- Compare-call action banks use a closed `action_bank.actions` list in strict provider output. Each action carries `operation_group`; deterministic update-state builders group the flat actions back into taxonomy or projection operation families.
	- Prompt snapshots for structured calls must record the provider response format, schema name, strict flag, target schema reference, target schema hash and exact target schema.

Isolated LLM Call Validation Policy
	- Every isolated LLM call must return strict JSON only.
	- Exception: user_report_samples and user_report_database are report-generation LLM calls. They return plain text/Markdown reports and are validated by the report rules in `15_llm_user_reports.md`, not by KernelJsonSchemaValidator strict JSON rules.
	- The Kernel must validate the returned JSON before any downstream Kernel function consumes it.
	- Validation is owned by KernelJsonSchemaValidator and the function-specific validation rules in specs 13 through 21.
	- Validation failures include:
		- invalid JSON
		- markdown or explanatory text outside JSON
		- schema_version mismatch
		- missing required fields
		- unknown fields where schemas are closed
		- enum mismatch
		- source fingerprint mismatch
		- taxonomy or projection fingerprint mismatch
		- sample ID or database reference mismatch
		- unknown taxonomy or projection code
		- invalid update-state family
		- invalid promotion path
		- validation rule violation defined by the function spec
	- Invalid LLM output must not be consumed by downstream Kernel functions.
	- Invalid LLM output must not mutate active_database state.
	- Invalid LLM output must be persisted as a failed attempt artifact for audit and debugging.

Isolated LLM Retry Policy
	- The Kernel must retry isolated LLM calls whose output fails JSON parsing or Kernel validation.
	- The retry budget is three attempts total:
		- attempt 1: initial isolated LLM call
		- attempt 2: validation-repair retry
		- attempt 3: final validation-repair retry
	- Retry attempts must use the same Kernel-owned input object, target schema and workflow state.
	- The Kernel may add compact validation feedback to the retry prompt.
	- The Kernel must not alter the semantic task, change workflow target, switch database, switch taxonomy/projection source, relax the schema or drop required content to make validation pass.
	- Each attempt must write:
		- prompt_snapshot
		- raw LLM response
		- parsed JSON when parsing succeeds
		- validation report
		- attempt metadata
	- Attempt artifacts must be written under the function's analysis/request run folder with attempt identity.
	- The validated output from the first successful attempt becomes the canonical output artifact for the LLM function.
	- Failed attempt artifacts remain available for support and audit, but are not consumed by downstream functions.
	- The user is not asked to intervene during internal retry.
	- The Agent may receive retry mirror events for awareness only when the Client Frontend needs live progress context.

Final LLM Validation Error Policy
	- If all three attempts fail validation, the Kernel must stop the current workflow at the failed LLM function.
	- The Kernel must not continue with partial, repaired-by-hand or best-effort JSON.
	- The Kernel must emit a final typed error to the Client Frontend/UserInteraction surface.
	- The same final error must be mirrored into the Agent context.
	- The final error object must include:
		- error_code
		- category: llm_validation
		- llm_function_name
		- workflow_run_id
		- analysis_run_id
		- attempted_schema
		- attempts_used
		- validation_error_summary
		- failed_attempt_artifact_refs
		- preserved_state_summary
		- recovery_options
		- support_bundle_ref
	- recovery_options must be Kernel-authored and may include:
		- retry_same_workflow
		- cancel_active_workflow
		- inspect_resume_state
		- support_only
	- recovery_options must be delivered through a Kernel auto-call mirror event.
	- Recovery tools for final LLM validation failure are event-scoped and must not be preloaded into the permanent Agent context window.
	- Tool mapping for recovery options:
		- retry_same_workflow exposes `kernel_retry_recoverable_workflow` when retry is allowed by preserved workflow state.
		- cancel_active_workflow exposes `kernel_cancel_active_run` when the workflow is still active or cancellable.
		- inspect_resume_state exposes `kernel_resume_state` when resumable state exists or may exist.
		- support_only exposes `kernel_open_support_bundle`.
		- apply_kernel_option may expose `kernel_apply_recovery_option` when the Kernel wants one bound recovery_id to be applied without exposing a more specific tool.
	- The final error must explain that the Kernel could not obtain valid structured JSON for the isolated LLM function after the retry budget was exhausted.
	- The final error must not expose raw stack traces or full raw LLM responses in user-facing text.

LLM Retry Mirror Events
	- Retry mirror events use event_type `llm_validation_retry`.
	- Final validation failure mirror events use event_type `llm_validation_failed_final`.
	- Retry mirror events must include:
		- llm_function_name
		- analysis_run_id
		- attempt_index
		- max_attempts
		- attempted_schema
		- validation_error_summary
		- next_kernel_action
	- Retry mirror events must not ask the Agent to repair JSON.
	- Final validation failure mirrors must follow `23_agent_facing_pipeline_manager_tools.md`.
