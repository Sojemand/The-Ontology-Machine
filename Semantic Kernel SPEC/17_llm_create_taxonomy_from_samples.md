# LLM Create Taxonomy From Sample Analyses

> Split from SPEC_Semantic_Runtime_Kernel_New.md.
> Source path: C:\Users\Norma\Workspace\The Ontology Machine\SPEC_Semantic_Runtime_Kernel_New.md.
> Source lines: 3462-3747.

Taxonomy authoring from sample analyses for create_custom_taxonomy precursor generation.

---

create_taxonomy_to_sample_analyses
	- the kernel sends the validated `kernel.sample_analyses.v1` JSON object from analyze_samples to an isolated LLM call with the prompt to generate a proposal about how the new taxonomy should be structured for the analyzed sample set and output the proposal in a defined json object that is then passed into:
		- create_taxonomy_update_state

	- Prompt Structure:
		```text
		You are the taxonomy proposal builder for the Semantic Runtime Kernel.

		You receive one validated `kernel.sample_analyses.v1` object. It describes the shared semantic content found across a sample set and contains a compact `taxonomy_seed`.

		Convert that seed into one strict taxonomy proposal JSON object. The proposal must be complete enough for the Kernel to validate it and transform it into the precursor used by `create_custom_taxonomy`.

		The taxonomy proposal defines the controlled vocabulary for normalization:
		- broad semantic domains across the human activity represented by the samples,
		- document types,
		- categories and subcategories,
		- scalar field codes,
		- repeated row types,
		- cell codes used inside rows.

		Create stable machine codes in ASCII snake_case. Keep the proposal compact. Include only terms that are supported by the sample-set analysis and relevant for normalization. Preserve the semantic relationships between terms:
		- document types must reference domains, allowed categories and allowed subcategories,
		- subcategories must reference their parent category,
		- field and cell codes must define value types,
		- row types may recommend the cell codes naturally expected inside that row type.

		For every term, provide a clear label, description and aliases. Descriptions should explain the semantic meaning of the term as reusable normalization vocabulary. Aliases may be empty when no stable alias is supported by the input.

		For field codes, set `promotion_slot` only when the field represents a document-level value that should be promoted into one of the proposal's taxonomy-owned Promotion Slots. Use null otherwise. Define any non-null slot in `taxonomy_proposal.promotion_slots`.

		Copy `sample_ids` from the input. Include `other` fallback terms and the exact `fallback_codes` object shown in the output schema.

		Return exactly one JSON object with schema_version `kernel.taxonomy_to_sample_analyses.v1`.
		Do not return Markdown or explanatory text outside the JSON.

		Input:
		{
		  "schema_version": "kernel.create_taxonomy_to_sample_analyses.input.v1",
		  "sample_analyses": {{kernel_sample_analyses_v1_json}}
		}
		```

	- json format:
		- Input Structure:
		```json
		{
		  "schema_version": "kernel.create_taxonomy_to_sample_analyses.input.v1",
		  "sample_analyses": "{{kernel_sample_analyses_v1_json}}"
		}
		```
		- `{{kernel_sample_analyses_v1_json}}` is the validated `kernel.sample_analyses.v1` object produced by the upstream `analyze_samples` function.
		- The Kernel either passes this object in memory from workflow state or loads it from `sample_analysis_requests/<analysis_run_id>/sample_analysis.json`.
		- The wrapped `sample_analyses` object is not rebuilt by `create_taxonomy_to_sample_analyses`.
		- Output must be strict JSON.
		- `schema_version`, `source_schema_version`, `analysis_scope`, `target` and `taxonomy_proposal.status` must use the exact constant values shown in the output schema.
		- `sample_ids` must match `kernel.sample_analyses.v1.sample_set.sample_ids`.
		- The Kernel validates with `additionalProperties=false` semantics for every object shape.
		- Unknown fields are invalid.
		- Missing required fields are invalid.
		- Empty strings are invalid unless a field explicitly allows null.
		- Arrays may be empty only where explicitly shown as review arrays, note arrays or term `aliases`.
		- Machine codes must be stable ASCII snake_case.
		- `value_type` must be one of:
			- `string`
			- `date_or_string`
			- `number_or_string`
			- `number_or_money_string`
		- `status` must be `active` for generated terms.
		- `other` is a reserved fallback code and must exist in domains, document types, categories, subcategories, field codes, row types and cell codes.
		- `fallback_codes` must map every fallback key to `other`.
		- `field_codes[*].promotion_slot` must be either null or one allowed promotion slot. Use null for ordinary fields that should remain only controlled field codes.
		- `validation.open_decisions`, `validation.warnings` and `quality.notes` contain compact validation-relevant strings and may be empty when nothing applies.
		- `quality.confidence` is a number from `0.0` to `1.0`.
		- The Kernel owns the final taxonomy ID. The LLM output must not create or propose `taxonomy_id`.
		- The LLM output is not `master.core.yaml` and not `master.text.en.yaml`; the Kernel derives those artifacts after validation.
		- The request/response artifacts must be written into the artifact tree for review and debug:
			- `taxonomy_to_sample_analysis_requests/<analysis_run_id>/create_taxonomy_to_sample_analyses.input.json`
			- `taxonomy_to_sample_analysis_requests/<analysis_run_id>/prompt_snapshot.json`
			- `taxonomy_to_sample_analysis_requests/<analysis_run_id>/llm_response.raw.json`
			- `taxonomy_to_sample_analysis_requests/<analysis_run_id>/taxonomy_to_sample_analyses.json`

		Output structure:
		```json
		{
		  "schema_version": "kernel.taxonomy_to_sample_analyses.v1",
		  "source_schema_version": "kernel.sample_analyses.v1",
		  "analysis_scope": "sample_set",
		  "sample_ids": ["sample_001"],
		  "target": {
		    "update_state_contract": "kernel.create_taxonomy_update_state.input.v1",
		    "custom_taxonomy_contract": "semantic_release_v1"
		  },
		  "taxonomy_proposal": {
		    "status": "draft",
		    "domains": [
		      {
		        "code": "candidate_domain",
		        "status": "active",
		        "label": "Candidate Domain",
		        "description": "Broad semantic domain represented by the sample set.",
		        "aliases": []
		      },
		      {
		        "code": "other",
		        "status": "active",
		        "label": "Other",
		        "description": "Fallback domain.",
		        "aliases": []
		      }
		    ],
		    "document_types": [
		      {
		        "code": "candidate_document_type",
		        "status": "active",
		        "label": "Candidate Document Type",
		        "description": "Stable document type represented by the sample set.",
		        "aliases": [],
		        "domains": ["candidate_domain"],
		        "allowed_categories": ["candidate_category", "other"],
		        "allowed_subcategories": ["candidate_subcategory", "other"]
		      },
		      {
		        "code": "other",
		        "status": "active",
		        "label": "Other",
		        "description": "Fallback document type for unclear or unsupported documents.",
		        "aliases": [],
		        "domains": ["other"],
		        "allowed_categories": ["other"],
		        "allowed_subcategories": ["other"]
		      }
		    ],
		    "categories": [
		      {
		        "code": "candidate_category",
		        "status": "active",
		        "label": "Candidate Category",
		        "description": "Reusable category supported by the sample set.",
		        "aliases": [],
		        "domains": ["candidate_domain"]
		      },
		      {
		        "code": "other",
		        "status": "active",
		        "label": "Other",
		        "description": "Fallback category.",
		        "aliases": [],
		        "domains": ["other"]
		      }
		    ],
		    "subcategories": [
		      {
		        "code": "candidate_subcategory",
		        "status": "active",
		        "label": "Candidate Subcategory",
		        "description": "Reusable subcategory under the candidate category.",
		        "aliases": [],
		        "parent_category": "candidate_category",
		        "domains": ["candidate_domain"]
		      },
		      {
		        "code": "other",
		        "status": "active",
		        "label": "Other",
		        "description": "Fallback subcategory.",
		        "aliases": [],
		        "parent_category": "other",
		        "domains": ["other"]
		      }
		    ],
		    "field_codes": [
		      {
		        "code": "document_number",
		        "status": "active",
		        "label": "Document Number",
		        "description": "Reusable scalar identifier field.",
		        "aliases": [],
		        "value_type": "string",
		        "domains": ["candidate_domain"],
		        "promotion_slot": "reference_number"
		      },
		      {
		        "code": "other",
		        "status": "active",
		        "label": "Other",
		        "description": "Fallback scalar field.",
		        "aliases": [],
		        "value_type": "string",
		        "domains": ["other"],
		        "promotion_slot": null
		      }
		    ],
		    "row_types": [
		      {
		        "code": "candidate_row",
		        "status": "active",
		        "label": "Candidate Row",
		        "description": "Repeated row structure supported by the sample set.",
		        "aliases": [],
		        "domains": ["candidate_domain"],
		        "recommended_cell_codes": ["description", "amount"]
		      },
		      {
		        "code": "other",
		        "status": "active",
		        "label": "Other",
		        "description": "Fallback row type.",
		        "aliases": [],
		        "domains": ["other"],
		        "recommended_cell_codes": ["other"]
		      }
		    ],
		    "cell_codes": [
		      {
		        "code": "description",
		        "status": "active",
		        "label": "Description",
		        "description": "Textual row description.",
		        "aliases": [],
		        "value_type": "string",
		        "domains": ["candidate_domain"]
		      },
		      {
		        "code": "amount",
		        "status": "active",
		        "label": "Amount",
		        "description": "Numeric or monetary row amount.",
		        "aliases": [],
		        "value_type": "number_or_money_string",
		        "domains": ["candidate_domain"]
		      },
		      {
		        "code": "other",
		        "status": "active",
		        "label": "Other",
		        "description": "Fallback cell code.",
		        "aliases": [],
		        "value_type": "string",
		        "domains": ["other"]
		      }
		    ],
		    "fallback_codes": {
		      "document_type": "other",
		      "category": "other",
		      "subcategory": "other",
		      "field_code": "other",
		      "row_type": "other",
		      "cell_code": "other"
		    }
		  },
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
		- Validate `schema_version`, `source_schema_version`, `analysis_scope` and required top-level fields.
		- Reject unknown object properties.
		- Reject `taxonomy_proposal.taxonomy_id`; the Kernel assigns taxonomy identity.
		- Validate `sample_ids` against `kernel.sample_analyses.v1.sample_set.sample_ids`.
		- Validate all machine codes as ASCII snake_case.
		- Reject duplicate `code` values within each taxonomy section.
		- Require fallback code `other` in domains and all controlled sections.
		- Validate every domain reference against `taxonomy_proposal.domains`.
		- Validate every `allowed_categories` item against `taxonomy_proposal.categories`.
		- Validate every `allowed_subcategories` item against `taxonomy_proposal.subcategories`.
		- Validate every `parent_category` against `taxonomy_proposal.categories`.
		- Validate every `recommended_cell_codes` item against `taxonomy_proposal.cell_codes`.
		- Validate every non-null `promotion_slot` against `taxonomy_proposal.promotion_slots`.
		- Validate every `value_type` against the allowed enum.
		- Validate `quality.confidence` as a number from `0.0` to `1.0`.
		- After validation, build the custom taxonomy precursor:
			- `master.core` from machine-stable fields and references.
			- `master.text.en.yaml` from labels, descriptions and aliases.
			- `field_codes[*].promotion_slot` into the taxonomy-owned Promotion Slot registry and downstream Projection Rule synthesis.
			- generic Kernel-owned `semantic_binding` for fields, rows and cells.
			- defaults, governance and compatibility from Kernel-owned policy.
		- Do not copy `validation`, `quality`, `target` or artifact paths into the final taxonomy.
