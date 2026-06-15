# LLM Analyze Samples

> Split from SPEC_Semantic_Runtime_Kernel_New.md.
> Source path: C:\Users\Norma\Workspace\The Ontology Machine\SPEC_Semantic_Runtime_Kernel_New.md.
> Source lines: 2382-2723.

analyze_samples prompt, input contract, output structure, taxonomy seed, projection seed, and report seed.

---

analyze_samples
	- the Kernel sends the sample documents to the pipeline extractor to generate optimizer `.raw` artifacts, builds one route-normalized `kernel.analyze_sample.input.v1` JSON object for each sample, and then sends those analyzer inputs to one isolated LLM call with the prompt to generate one sample-set analysis based on the document semantic structure with a defined json object format that is passed into the functions:
		- user_report_samples
		- create_projections_to_sample_analyses
		- create_taxonomy_to_sample_analyses
		- create_taxonomy_to_sample_analyses
		- create_projections_to_sample_analyses

	- Prompt Structure:
		```text
		You are the semantic sample-set analyzer for the Semantic Runtime Kernel.

		You receive a JSON array of `kernel.analyze_sample.input.v1` objects. Each object represents one sample document in the same normalized input format. The samples together represent a document family or semantic processing target. Analyze them as a set.

		Your goal is to derive the shared semantic structure that is useful for creating or refining taxonomy and projection definitions. Focus on the shared document family, stable patterns, and expected or structurally relevant variations across the samples. Mention sample variation only when it affects taxonomy or projection design.

		Taxonomy context:
		A taxonomy is the controlled semantic vocabulary of the runtime. It defines reusable semantic building blocks that downstream processing can assign to documents and extracted content.

		A taxonomy is organized into:

		- `domains`: broad semantic areas of human activity and human-made records. Domains can cover work, institutions, households, identity, health, care, learning, housing, finance, law, administration, technology, logistics, community, belief, personal life, creative expression, wellbeing, and other stable spheres of activity. Derive domain candidates from the semantic world represented by the sample set, including non-standard or newly observed domains when they are clearly useful.
		- `document_types`: recognizable document kinds within one or more domains, such as invoice, certificate, application, report, personal_note, treatment_plan, maintenance_record, membership_record, or another stable kind found in the samples.
		- `categories`: higher-level semantic groupings that organize document content across document types.
		- `subcategories`: narrower groupings under categories that help separate recurring semantic intents or subject areas.
		- `field_codes`: reusable codes for scalar document fields, such as document_number, due_date, person_name, property_address, total_amount, diagnosis, event_name, or contact_person.
		- `row_types`: semantic types for repeated table or list rows, such as line_item, payment_schedule, participant_list, timeline_entry, medication_schedule, measurement_series, or another repeated structure found in the samples.
		- `cell_codes`: reusable codes for cells, columns, or repeated row attributes, such as description, quantity, amount, status, name, role, date, dosage, frequency, note, or identifier.

		The taxonomy should capture reusable semantics from the sample set. Candidate codes should be compact, stable, lowercase snake_case identifiers.

		Projection context:
		A projection is an operational view over the taxonomy. It selects the taxonomy elements that should be available together for one coherent processing context.

		A projection is used to keep runtime prompts and normalization work focused. It should be large enough to cover the shared semantic family represented by the samples, and small enough to avoid carrying unrelated taxonomy into the next LLM call.

		Projection size guidance:
		A projection may cover more than one narrow concept family when those concepts appear together in the same sample set or document context. Prefer broad coverage over premature splitting.

		If the sample-derived taxonomy is small enough to fit comfortably into one projection, keep it in one projection. As a practical scale, a projection with tens of included taxonomy codes is normal, and a projection reaching the low hundreds of included codes is still acceptable when it preserves complete document coverage.

		Split into multiple projections only when one combined projection would become clearly too large for efficient prompting, or when the sample set contains genuinely separate document contexts that should not be normalized together.

		For the normalizer, a single sufficiently complete projection is often better than several narrow projections. It gives the normalizer the full semantic context of the document, reduces the chance that relevant content falls outside the active projection, and minimizes fallback assignments such as `other`, which would otherwise create unnecessary review signals.

		A projection contains:
		- `projection_id`, `label`, and `description`: identity and purpose.
		- `domain_ids`: the taxonomy domains covered by the projection.
		- `include_document_types`, `include_categories`, `include_subcategories`: classification scope.
		- `include_field_codes`: scalar fields expected or preserved by the runtime.
		- `include_row_types` and `include_cell_codes`: repeated structures and their attributes.
		- `routing`: compact signals that help choose this projection.
		- `routing_lexicon`: text markers and domain markers that indicate relevance.
		- `promotion_rules`: mappings from taxonomy-defined document-level fields or facets into runtime slots that make this document family useful for search, filtering, display, grouping, routing or later retrieval.

		The projection should describe the narrowest complete operational boundary that still covers the sample set.

		Task:
		Create one compact `kernel.sample_analyses.v1` JSON object.

		The output must give downstream functions enough structure to:
		- create candidate taxonomy nodes,
		- create candidate projections,
		- compare sample-derived semantics against existing runtime structures,
		- explain the analysis to a user in a comprehensive report.

		Analyze the samples as one collective semantic set. Prefer stable shared findings over isolated one-off details.

		Construction rules:
		- `sample_set` describes the shared semantic shape across all samples.
		- `taxonomy_seed` contains reusable candidate vocabulary derived from the sample set.
		- `projection_seed` contains candidate operational views that reference the codes from `taxonomy_seed`.
		- `projection_seed.projections[*].include_*` lists should contain the relevant candidate taxonomy codes plus fallback `other` where appropriate.
		- `promotion_rules` should cover the document-level fields or facets that make this document family useful at runtime. Prefer a compact but useful slot set over a sparse one, and use multi-value promotion candidates for repeatable facets that naturally have several values per document.
		- `user_report_samples_seed` should be detailed enough for a user-facing report to explain what the sample set contains from taxonomy and projection perspective.
		- Descriptive and report-facing strings must be non-empty and substantive.
		- Array fields for variations, decisions, risks and notes contain concise strings; use an empty array only when there is genuinely nothing to report.
		- Keep candidate codes compact, stable, and lowercase snake_case.
		- Keep the JSON concise, but make the report seed substantive.

		Return valid JSON only.

		Input:
		{{kernel_analyze_sample_inputs_json}}
		```

	- json format:
		- analyze_samples does not send optimizer `.raw` directly to the isolated LLM call.
		- The optimizer `.raw` is only an intermediate extractor artifact.
		- The Kernel first builds a route-specific interpreter-request view, then normalizes it into `kernel.analyze_sample.input.v1`.
		- Supported route-specific input views:
			- `interpreter_request_view_vision.v1`
				- built from scan/image-heavy ingestion routes.
				- uses the same treated JSON content family as the Interpreter request.
				- does not transport `page_assets`, image blocks, image paths or `image_detail`.
			- `interpreter_request_view_file.v1`
				- built from born-digital/file extraction routes.
				- uses the same treated JSON content family as the Interpreter request.
				- does not transport `page_assets`, file/image asset paths or `image_detail`.
		- Both route-specific views are normalized into one sample-format-agnostic input shape before the LLM call.
		- `source_ref.kind` must be `interpreter_request_view_vision.v1` or `interpreter_request_view_file.v1`.
		- `route.ingestion_profile` and `route.interpreter_profile` must reflect the source route (`vision` or `file`), while the analyzer output remains route-agnostic.
		- `kernel.analyze_sample.input.v1` is pure JSON content. It is not an evidence contract and not a visual verification contract.
		- No `projection_catalog`, projection hint, taxonomy id, projection id, include list or existing controlled code may be present in the analyzer input.
		- No semantic document content may be truncated, capped or omitted for prompt-budget reasons.
		- Interpreter prompt rendering limits such as max sections, max section chars, max tables or max table rows must not be applied to `kernel.analyze_sample.input.v1`.
		- Prompt-noise and runtime-only fields may be removed:
			- `page_assets`
			- `image_detail`
			- `file_reference`
			- asset paths
			- nested `_source_refs`
			- nested `block_ids`
			- nested `block_refs`
			- `runtime_trace`
			- `compression_audit`
			- `projection_catalog`
		- The generated request JSON and LLM artifacts are written into one sample-set analysis run folder for log, review and debug purposes:
			- `sample_analysis_requests/<analysis_run_id>/inputs/<sample_id>/analyze_sample.input.json`
			- `sample_analysis_requests/<analysis_run_id>/prompt_snapshot.json`
			- `sample_analysis_requests/<analysis_run_id>/llm_response.raw.json`
			- `sample_analysis_requests/<analysis_run_id>/sample_analysis.json`

		Input contract:
		```json
		{
		  "schema_version": "kernel.analyze_sample.input.v1",
		  "sample_id": "sample_001",
		  "source_ref": {
		    "kind": "interpreter_request_view_vision.v1",
		    "artifact_path": "sample_analysis_requests/analysis_run_001/inputs/sample_001/analyze_sample.input.json"
		  },
		  "route": {
		    "ingestion_profile": "vision",
		    "interpreter_profile": "vision",
		    "input_modality": "scan_or_image",
		    "is_scan": true,
		    "language": "de"
		  },
		  "document": {
		    "source": {
		      "file_name": "sample.pdf",
		      "file_ext": "pdf",
		      "content_hash": "sha256:...",
		      "page_count": 1,
		      "document_type": "unknown",
		      "language": "de",
		      "size_bytes": null,
		      "created_at": null,
		      "modified_at": null,
		      "is_scan": true,
		      "has_handwriting": false
		    },
		    "context": {},
		    "extracted_content": {
		      "summary": {},
		      "sections": [
		        {
		          "id": "section_001",
		          "page": 1,
		          "role": "header",
		          "text": "Full extracted section text without prompt truncation."
		        }
		      ],
		      "facts": {
		        "observed_fact_name": {
		          "value": "observed value",
		          "confidence": null,
		          "page": 1
		        }
		      },
		      "tables": [
		        {
		          "id": "table_001",
		          "page": 1,
		          "role": "observed_table",
		          "headers": ["column_a", "column_b"],
		          "rows": [
		            {
		              "cells": {
		                "column_a": "value a",
		                "column_b": "value b"
		              }
		            }
		          ]
		        }
		      ]
		    }
		  },
		  "completeness": {
		    "semantic_content_complete": true,
		    "prompt_budget_truncation_applied": false,
		    "omitted_semantic_content": [],
		    "notes": []
		  }
		}
		```

		Output structure:
		```json
		{
		  "schema_version": "kernel.sample_analyses.v1",
		  "analysis_scope": "sample_set",
		  "input_contract": "kernel.analyze_sample.input.v1",
		  "sample_set": {
		    "sample_ids": ["sample_001"],
		    "summary": "Compact description of what the samples show together.",
		    "document_family": "candidate_document_family",
		    "shared_semantic_pattern": "Stable semantic structure shared across the sample set.",
		    "meaningful_variations": ["Concise variation that affects taxonomy or projection design."],
		    "classification": {
		      "domain_codes": ["candidate_domain"],
		      "document_type_codes": ["candidate_document_type"],
		      "category_codes": ["candidate_category"],
		      "subcategory_codes": ["candidate_subcategory"],
		      "confidence": 0.0
		    },
		    "structure": {
		      "shape": "mixed",
		      "section_roles": ["header", "body"],
		      "party_roles": ["issuer", "recipient"]
		    },
		    "signals": {
		      "labels": ["Document number", "Amount"],
		      "text_markers": ["invoice"]
		    }
		  },
		  "taxonomy_seed": {
		    "domains": [
		      {"code": "candidate_domain", "label": "Candidate domain", "description": "Semantic area represented by the sample set."}
		    ],
		    "document_types": [
		      {
		        "code": "candidate_document_type",
		        "label": "Candidate document type",
		        "description": "Stable document kind represented by the sample set.",
		        "domains": ["candidate_domain"],
		        "allowed_categories": ["candidate_category"],
		        "allowed_subcategories": ["candidate_subcategory"]
		      }
		    ],
		    "categories": [
		      {"code": "candidate_category", "label": "Candidate category", "description": "Reusable content grouping observed in the sample set.", "domains": ["candidate_domain"]}
		    ],
		    "subcategories": [
		      {"code": "candidate_subcategory", "label": "Candidate subcategory", "description": "More specific grouping under the candidate category.", "parent_category": "candidate_category", "domains": ["candidate_domain"]}
		    ],
		    "field_codes": [
		      {"code": "document_number", "label": "Document number", "description": "Reusable scalar identifier field.", "value_type": "string", "domains": ["candidate_domain"], "promotion_slot": "reference_number"}
		    ],
		    "row_types": [
		      {"code": "line_item", "label": "Line item", "description": "Repeated item row observed across the sample set.", "domains": ["candidate_domain"], "recommended_cell_codes": ["description", "amount"]}
		    ],
		    "cell_codes": [
		      {"code": "description", "label": "Description", "description": "Textual row or item description.", "value_type": "string", "domains": ["candidate_domain"]},
		      {"code": "amount", "label": "Amount", "description": "Numeric or monetary amount value.", "value_type": "number_or_money_string", "domains": ["candidate_domain"]}
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
		  "projection_seed": {
		    "projections": [
		      {
		        "projection_id": "candidate_domain.custom.v1",
		        "label": "Candidate projection",
		        "description": "Complete operational view for the sample-derived document family.",
		        "domain_ids": ["candidate_domain"],
		        "include_document_types": ["candidate_document_type", "other"],
		        "include_categories": ["candidate_category", "other"],
		        "include_subcategories": ["candidate_subcategory", "other"],
		        "include_field_codes": ["document_number", "other"],
		        "include_row_types": ["line_item", "other"],
		        "include_cell_codes": ["description", "amount", "other"],
		        "promotion_rules": [
		          {"slot": "reference_number", "source_paths": ["content.fields.document_number"]},
		          {"slot": "description", "source_paths": ["context.description"]}
		        ],
		        "routing": {
		          "when_to_use": "Use for documents matching the shared semantic pattern of the sample set.",
		          "avoid_when": "Use another projection when the document belongs to a clearly different semantic context.",
		          "example_document_types": ["candidate_document_type"],
		          "section_roles": ["header", "body", "other"],
		          "party_roles": ["issuer", "recipient", "other"]
		        },
		        "routing_lexicon": {
		          "text_markers": ["invoice"],
		          "domain_markers": [
		            {"domain_id": "candidate_domain", "markers": ["invoice"]}
		          ]
		        }
		      }
		    ]
		  },
		  "user_report_samples_seed": {
		    "report_purpose": "Explain what the sample set shows and what it means for taxonomy and projection design.",
		    "taxonomy_view": {
		      "domain_findings": "What domain candidates the sample set supports and why.",
		      "document_type_findings": "What document type candidates are supported by the shared sample structure.",
		      "category_findings": "Which category and subcategory candidates organize the observed semantics.",
		      "field_code_findings": "Which scalar field candidates matter for downstream normalization.",
		      "row_and_cell_findings": "Which repeated row and cell candidates matter for structured content.",
		      "taxonomy_gaps_or_decisions": ["Concise taxonomy decision or open point for user review."]
		    },
		    "projection_view": {
		      "projection_boundary_findings": "Why the proposed projection boundary covers the sample set.",
		      "included_semantics": "Which taxonomy candidates are included and why they belong together.",
		      "routing_findings": "Which text markers, document types and roles support projection routing.",
		      "promotion_rule_findings": "Which values are important enough to promote into runtime slots.",
		      "split_or_merge_considerations": "Whether one projection is sufficient or a split is justified.",
		      "projection_gaps_or_decisions": ["Concise projection decision or open point for user review."]
		    },
		    "sample_set_findings": {
		      "what_the_samples_show_together": "Comprehensive description of the shared semantic content across the samples.",
		      "taxonomy_relevance": "How the shared content maps into reusable taxonomy candidates.",
		      "projection_relevance": "How the shared content should be covered by the candidate projection."
		    },
		    "recommended_user_decisions": ["Concise user decision needed before promotion or validation."],
		    "report_risks_or_uncertainties": ["Concise uncertainty that affects taxonomy or projection design."]
		  },
		  "quality": {
		    "confidence": 0.0,
		    "notes": ["Concise quality note."]
		  }
		}
		```
		- `kernel.sample_analyses.v1` is a sample-set analysis seed, not a validated taxonomy or projection proposal.
		- `sample_set` describes the shared document family and stable semantic coverage across all samples; variations are included only when they affect taxonomy or projection design.
		- Output artifact references are attached by the Kernel outside the LLM result; the LLM output only needs `sample_set.sample_ids`.
		- It uses taxonomy/projection-friendly local candidate codes, but keeps only fields needed by downstream consumers.
		- `taxonomy_seed` is the compact source for downstream master taxonomy creation or comparison.
		- `projection_seed.projections[*].include_*` must reference candidate codes from `taxonomy_seed`, plus fallback `other`.
		- `projection_seed` should prefer one complete projection when the sample-derived taxonomy comfortably fits into one operational context.
		- `sample_set.structure.shape` must be one of: `text`, `form`, `table`, `form_with_table`, `list`, `mixed`.
		- String arrays such as `meaningful_variations`, `taxonomy_gaps_or_decisions`, `projection_gaps_or_decisions`, `recommended_user_decisions`, `report_risks_or_uncertainties` and `quality.notes` contain concise strings and may be empty when nothing applies.
		- `user_report_samples_seed` must be comprehensive enough for `user_report_samples` to explain the sample-set analysis from taxonomy and projection perspective without re-reading the sample inputs.
		- `user_report_samples_seed` must stay grounded in `sample_set`, `taxonomy_seed` and `projection_seed`; it must not introduce new candidate codes.
		- Downstream functions may promote, rename, merge or discard candidate codes when creating validated taxonomy/projection proposals.
