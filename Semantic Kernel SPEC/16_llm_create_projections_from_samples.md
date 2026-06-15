# LLM Create Projections From Sample Analyses

> Split from SPEC_Semantic_Runtime_Kernel_New.md.
> Source path: C:\Users\Norma\Workspace\The Ontology Machine\SPEC_Semantic_Runtime_Kernel_New.md.
> Source lines: 3243-3461.

Projection authoring from sample analyses and taxonomy authoring view.

---

create_projections_to_sample_analyses
	- the kernel sends the validated `kernel.sample_analyses.v1` JSON object from analyze_samples together with a compact taxonomy authoring view to an isolated LLM call with the prompt to generate a proposal about how one or more projections should be derived from the designated taxonomy and structured for the analyzed sample set. The output proposal is passed into:
		- create_projections_update_state

	- Prompt Structure:
		```text
		You are the projection proposal builder for the Semantic Runtime Kernel.

		You receive:
		1. one validated `kernel.sample_analyses.v1` object,
		2. one `kernel.taxonomy_projection_authoring_view.v1` object.

		The sample analysis describes the shared semantic content found across a sample set.
		The taxonomy authoring view is the compact projection-facing view of the designated taxonomy. It contains the allowed taxonomy codes, short term summaries, relevant relationships, fallback codes and promotion slots needed for projection design.

		Create one strict projection proposal JSON object. The proposal must be complete enough for the Kernel to validate it against the real taxonomy and transform it into the precursor used by `create_custom_projection`.

		A projection is the operational view used by the Normalizer. It selects which taxonomy codes are visible together during normalization and provides routing text and routing markers for that view.

		Prefer one complete projection when the sample-derived semantic content fits comfortably into one operational context, even if several concept families are mixed. Split into multiple projections only when one projection would become too broad for reliable routing or when the sample analysis clearly describes distinct operational contexts.

		Every included code must come from the taxonomy authoring view. Include `other` fallback codes in every include list.

		For each projection, provide:
		- stable projection_id,
		- label and description,
		- domain_ids,
		- include_document_types, include_categories, include_subcategories,
		- include_field_codes, include_row_types, include_cell_codes,
		- promotion_rules for the projection's taxonomy-defined promotion slots,
		- routing.when_to_use and routing.avoid_when,
		- routing.example_document_types, section_roles and party_roles,
		- routing_lexicon.text_markers and routing_lexicon.domain_markers as closed domain marker entries.

		Promotion rules must map each useful slot exposed by the taxonomy authoring view to the Normalizer content path
		that can fill it. Prefer `content.fields.<field_code>` when the slot is backed by a scalar or multi document
		field. Do not omit a slot merely because related evidence also appears in rows; rows preserve structure, while
		promotion rules materialize the document-level runtime surface.

		Copy `sample_ids` from the input. Return exactly one JSON object with schema_version `kernel.projections_to_sample_analyses.v1`.
		Do not return Markdown or explanatory text outside the JSON.

		Input:
		{
		  "schema_version": "kernel.create_projections_to_sample_analyses.input.v1",
		  "sample_analyses": {{kernel_sample_analyses_v1_json}},
		  "taxonomy_authoring_view": {{kernel_taxonomy_projection_authoring_view_v1_json}}
		}
		```

	- json format:
		- Input Structure:
		```json
		{
		  "schema_version": "kernel.create_projections_to_sample_analyses.input.v1",
		  "sample_analyses": "{{kernel_sample_analyses_v1_json}}",
		  "taxonomy_authoring_view": "{{kernel_taxonomy_projection_authoring_view_v1_json}}"
		}
		```
		- `{{kernel_sample_analyses_v1_json}}` is the validated `kernel.sample_analyses.v1` object produced by the upstream `analyze_samples` function.
		- `{{kernel_taxonomy_projection_authoring_view_v1_json}}` is built deterministically by the Kernel from the active or staged taxonomy before this LLM call.
		- The authoring view is not the real taxonomy schema. It is a compact semantic adapter for LLM projection design.
		- The authoring view prevents progressive prompt growth by replacing full `master.core`, locale text files and release metadata with only projection-relevant taxonomy semantics.
		- The Kernel keeps the real taxonomy and validates the LLM output against it after the call.

		Input authoring view structure:
		```json
		{
		  "schema_version": "kernel.taxonomy_projection_authoring_view.v1",
		  "taxonomy_ref": {
		    "source": "active",
		    "taxonomy_fingerprint": "sha256:...",
		    "runtime_locale": "en"
		  },
		  "budget_policy": {
		    "view_mode": "complete",
		    "complete_code_lists_available": true,
		    "term_summaries_are_sliced": false,
		    "notes": []
		  },
		  "allowed_codes": {
		    "domains": ["candidate_domain", "other"],
		    "document_types": ["candidate_document_type", "other"],
		    "categories": ["candidate_category", "other"],
		    "subcategories": ["candidate_subcategory", "other"],
		    "field_codes": ["document_number", "other"],
		    "row_types": ["candidate_row", "other"],
		    "cell_codes": ["description", "amount", "other"]
		  },
		  "term_summaries": {
		    "domains": [
		      {"code": "candidate_domain", "label": "Candidate Domain", "description": "Short semantic description."}
		    ],
		    "document_types": [
		      {"code": "candidate_document_type", "label": "Candidate Document Type", "description": "Short semantic description.", "domains": ["candidate_domain"], "allowed_categories": ["candidate_category", "other"], "allowed_subcategories": ["candidate_subcategory", "other"]}
		    ],
		    "categories": [
		      {"code": "candidate_category", "label": "Candidate Category", "description": "Short semantic description.", "domains": ["candidate_domain"]}
		    ],
		    "subcategories": [
		      {"code": "candidate_subcategory", "label": "Candidate Subcategory", "description": "Short semantic description.", "parent_category": "candidate_category", "domains": ["candidate_domain"]}
		    ],
		    "field_codes": [
		      {"code": "document_number", "label": "Document Number", "description": "Short semantic description.", "value_type": "string", "domains": ["candidate_domain"], "promotion_slot": "document_number"}
		    ],
		    "row_types": [
		      {"code": "candidate_row", "label": "Candidate Row", "description": "Short semantic description.", "domains": ["candidate_domain"], "recommended_cell_codes": ["description", "amount"]}
		    ],
		    "cell_codes": [
		      {"code": "description", "label": "Description", "description": "Short semantic description.", "value_type": "string", "domains": ["candidate_domain"]},
		      {"code": "amount", "label": "Amount", "description": "Short semantic description.", "value_type": "number_or_money_string", "domains": ["candidate_domain"]}
		    ]
		  },
		  "promotion_slots": [
		    {"slot": "document_number", "value_type": "string"},
		    {"slot": "document_date", "value_type": "date_or_string"}
		  ],
		  "fallback_codes": {
		    "document_type": "other",
		    "category": "other",
		    "subcategory": "other",
		    "field_code": "other",
		    "row_type": "other",
		    "cell_code": "other"
		  }
		}
		```

		Authoring view rules:
		- `taxonomy_ref.source` must be one of: `active`, `staged`, `custom_taxonomy_update_state`.
		- `budget_policy.view_mode` must be one of: `complete`, `relevant_slice`.
		- `allowed_codes` is the hard code boundary for the LLM output.
		- `term_summaries` may be complete for small taxonomies or sliced for large taxonomies.
		- If `term_summaries` is sliced, `allowed_codes` still contains the complete valid code lists needed for validation.
		- The Kernel builds relevant slices from `kernel.sample_analyses.v1.taxonomy_seed`, related taxonomy relationships, fallback codes and promotion slots.
		- The LLM must not invent taxonomy codes. If a needed code is missing from `allowed_codes`, it must add a compact note to `validation.open_decisions` instead of using the missing code.
		- The request/response artifacts must be written into the artifact tree for review and debug:
			- `projection_to_sample_analysis_requests/<analysis_run_id>/create_projections_to_sample_analyses.input.json`
			- `projection_to_sample_analysis_requests/<analysis_run_id>/taxonomy_projection_authoring_view.json`
			- `projection_to_sample_analysis_requests/<analysis_run_id>/prompt_snapshot.json`
			- `projection_to_sample_analysis_requests/<analysis_run_id>/llm_response.raw.json`
			- `projection_to_sample_analysis_requests/<analysis_run_id>/projections_to_sample_analyses.json`

		Output structure:
		```json
		{
		  "schema_version": "kernel.projections_to_sample_analyses.v1",
		  "source_schema_version": "kernel.sample_analyses.v1",
		  "taxonomy_view_schema_version": "kernel.taxonomy_projection_authoring_view.v1",
		  "analysis_scope": "sample_set",
		  "sample_ids": ["sample_001"],
		  "taxonomy_ref": {
		    "source": "active",
		    "taxonomy_fingerprint": "sha256:..."
		  },
		  "target": {
		    "update_state_contract": "kernel.create_projections_update_state.input.v1",
		    "custom_projection_contract": "semantic_release_v1"
		  },
		  "projection_strategy": {
		    "mode": "single_projection",
		    "reason": "One projection covers the sample-set semantics without losing operational context."
		  },
		  "projection_proposals": [
		    {
		      "projection_id": "candidate_domain.default.v1",
		      "label": "Candidate Projection",
		      "description": "Operational view for the sample-derived document family.",
		      "domain_ids": ["candidate_domain"],
		      "include_document_types": ["candidate_document_type", "other"],
		      "include_categories": ["candidate_category", "other"],
		      "include_subcategories": ["candidate_subcategory", "other"],
		      "include_field_codes": ["document_number", "other"],
		      "include_row_types": ["candidate_row", "other"],
		      "include_cell_codes": ["description", "amount", "other"],
		      "promotion_rules": [
		        {"slot": "document_number", "source_paths": ["content.fields.document_number"]}
		      ],
		      "routing": {
		        "when_to_use": "Use for documents matching the shared semantic pattern of the sample set.",
		        "avoid_when": "Use another projection when the document belongs to a clearly different semantic context.",
		        "example_document_types": ["candidate_document_type"],
		        "section_roles": ["header", "body", "other"],
		        "party_roles": ["issuer", "recipient", "other"]
		      },
		      "routing_lexicon": {
		        "text_markers": ["candidate"],
		        "domain_markers": [
		          {"domain_id": "candidate_domain", "markers": ["candidate"]}
		        ]
		      }
		    }
		  ],
		  "validation": {
		    "open_decisions": [],
		    "warnings": []
		  },
		  "quality": {
		    "confidence": 0.0,
		    "notes": []
		  }
		}
		```

		Kernel validation:
		- Validate `schema_version`, `source_schema_version`, `taxonomy_view_schema_version`, `analysis_scope` and required top-level fields.
		- Reject unknown object properties.
		- Validate `sample_ids` against `kernel.sample_analyses.v1.sample_set.sample_ids`.
		- Validate `taxonomy_ref.source` against the allowed source enum.
		- Validate `taxonomy_ref.taxonomy_fingerprint` against the taxonomy authoring view and the real taxonomy.
		- Validate every projection ID as a stable ASCII projection ID.
		- Validate every included code against `taxonomy_authoring_view.allowed_codes` and then against the real taxonomy.
		- Require `other` in every include list.
		- Validate `routing.example_document_types` as a subset of `include_document_types`.
		- Validate `routing_lexicon.domain_markers[*].domain_id` as included `domain_ids`.
		- Validate every `promotion_rules[*].slot` against `taxonomy_authoring_view.promotion_slots`.
		- Validate every `promotion_rules[*].source_paths` entry as a compact Normalizer source path.
		- Validate `quality.confidence` as a number from `0.0` to `1.0`.
		- After validation, build the custom projection precursor:
			- projection core from machine-stable include lists, promotion rules and routing roles.
			- projection text from label, description, `routing.when_to_use`, `routing.avoid_when` and `routing_lexicon`.
			- materialization profile, projection family, compatibility and locale scaffolding from Kernel-owned policy.
		- Do not copy `validation`, `quality`, `target`, authoring view budget metadata or artifact paths into the final projection.
