from __future__ import annotations

from textwrap import dedent


USER_PROMPT = dedent(
    """
You are the projection proposal builder for the Semantic Runtime Kernel.

You receive:
1. one validated `kernel.sample_analyses.v1` object,
2. one `kernel.taxonomy_projection_authoring_view.v1` object.

The sample analysis describes the shared semantic content found across a sample set.
The taxonomy authoring view is the complete projection-facing view of the designated taxonomy. It contains all
allowed taxonomy codes, short term summaries, relevant relationships, fallback codes and promotion slots needed
for projection design.

Taxonomy context:
A taxonomy is the controlled semantic vocabulary of the runtime. It defines domains, document types, categories,
subcategories, field codes, row types and cell codes that downstream normalization can assign to documents and
extracted content.

Projection context:
A projection is the operational view used by the Normalizer. It selects which taxonomy codes are visible
together during normalization and provides routing text, routing roles, routing markers and promotion rules for
that view.

Create one strict projection proposal JSON object. The proposal must be complete enough for the Kernel to
validate it against the real taxonomy and transform it into the precursor used by `create_custom_projection`.

Prefer one projection when the sample-derived semantic content can be normalized as one coherent operational
context, even if it contains several concept families. A single projection should still preserve distinct
surfaces: promotion rules for top-level runtime facets, include_field_codes for scalar detail,
include_row_types/include_cell_codes for repeated structures, and routing text for section, clause, paragraph,
or wrapper/body differences. Split into multiple projections only when one projection would become too broad
for reliable routing or when the sample analysis clearly describes distinct operational contexts.

Every included code must come from the taxonomy authoring view. Include `other` fallback codes in every include
list.

For each projection, provide:
- stable projection_id,
- status,
- label and description,
- domain_ids,
- include_document_types, include_categories, include_subcategories,
- include_field_codes, include_row_types, include_cell_codes,
- promotion_rules for the projection's taxonomy-defined promotion slots,
- routing.when_to_use and routing.avoid_when,
- routing.example_document_types, section_roles and party_roles,
- routing_lexicon.text_markers and routing_lexicon.domain_markers as a list of domain marker entries.

Promotion rules must map each useful slot exposed by the taxonomy authoring view to the Normalizer content path
that can fill it. Use `content.fields.<field_code>` when the slot is backed by a document-level scalar or multi
field. Use row/cell-derived paths only when the slot represents a document-level summary facet rather than a
row-local value. Do not omit a slot merely because related evidence also appears in rows; rows preserve
structure, while promotion rules materialize the document-level runtime surface.
Only include a promotion rule when it has at least one concrete source path. If a slot cannot be mapped from
the included fields, rows, cells, context, or structure, omit that rule entirely; never emit an empty
`source_paths` array.

Copy `sample_ids` from the input. Return exactly one JSON object with schema_version `kernel.projections_to_sample_analyses.v1`.
Do not return Markdown or explanatory text outside the JSON.

Input:
{input_json}{validation_feedback_block}
    """
).strip()

OUTPUT_APPENDIX = dedent(
    """
Output structure:
```json
{
  "schema_version": "kernel.projections_to_sample_analyses.v1",
  "source_schema_version": "kernel.sample_analyses.v1",
  "taxonomy_view_schema_version": "kernel.taxonomy_projection_authoring_view.v1",
  "analysis_scope": "sample_set",
  "sample_ids": ["sample_001"],
  "taxonomy_ref": {"source": "active", "taxonomy_id": "normalizer_taxonomy.master", "taxonomy_version": "2026-05-01.v1", "taxonomy_fingerprint": "sha256:tax001"},
  "target": {"update_state_contract": "kernel.create_projections_update_state.input.v1"},
  "projection_strategy": {"mode": "single_projection", "rationale": "One projection covers the sample-set semantics without losing operational context.", "projection_count": 1},
  "projection_proposals": [
    {
      "projection_id": "finance.receipts.v1",
      "status": "draft",
      "label": "Finance Receipts",
      "description": "Receipt-oriented finance projection.",
      "domain_ids": ["finance"],
      "include_document_types": ["invoice", "other"],
      "include_categories": ["finance", "other"],
      "include_subcategories": ["other"],
      "include_field_codes": ["issuer", "amount_due", "other"],
      "include_row_types": ["line_item", "other"],
      "include_cell_codes": ["description", "other"],
      "promotion_rules": [{"slot": "counterparty", "source_paths": ["content.fields.issuer"]}],
      "routing": {"when_to_use": "Use for finance receipts.", "avoid_when": "Avoid for non-finance documents.", "example_document_types": ["invoice"], "section_roles": ["header", "body"], "party_roles": []},
      "routing_lexicon": {"text_markers": [], "domain_markers": [{"domain_id": "finance", "markers": []}]}
    }
  ],
  "validation": {"status": "passed", "open_decisions": [], "warnings": []},
  "quality": {"confidence": 0.0, "notes": []}
}
```

Kernel validation:
- Validate schema/source/scope/sample IDs and reject unknown object properties.
- Validate taxonomy source/fingerprint against the authoring view and real taxonomy.
- Validate projection IDs, all included codes, required `other` fallbacks, routing references, promotion slots and source paths.
- Build the custom projection precursor from include lists, promotion rules, routing roles, text and `routing_lexicon`.
    """
).strip()
