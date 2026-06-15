from __future__ import annotations

from textwrap import dedent


USER_PROMPT = dedent(
    """
You are the taxonomy proposal builder for the Semantic Runtime Kernel.

You receive one validated `kernel.sample_analyses.v1` object. It describes the shared semantic content found
across a sample set and contains a compact `taxonomy_seed`.

Convert that seed into one strict taxonomy proposal JSON object. The proposal must be complete enough for the
Kernel to validate it and transform it into the precursor used by `create_custom_taxonomy`.

The taxonomy proposal defines the controlled vocabulary for normalization:
- broad semantic domains across the human activity represented by the samples,
- document types,
- categories and subcategories,
- scalar field codes,
- repeated row types,
- cell codes used inside rows.

Create stable machine codes in ASCII snake_case. This step materializes `taxonomy_seed`; it is not a second
taxonomy design pass. Preserve every valid in-scope seed term. Do not re-compress, replace or reinterpret the
vocabulary merely to make the proposal smaller. Compact means concise, reusable and non-duplicative; it does
not mean sparse.

Only merge or omit a seed term when it is invalid, duplicated, only a wording variant better represented as an
alias, or outside the sample document family. Add required `other` fallback terms and the relationship fields
needed by the output schema. If a generic carrier term and a specialized term both appear in the seed and serve
different assignments, keep both.

Preserve the semantic relationships between terms:
- document types must reference domains, allowed categories and allowed subcategories,
- subcategories must reference their parent category,
- field and cell codes must define value types,
- row types may recommend the cell codes naturally expected inside that row type.

For every term, provide a clear label, description and aliases. Descriptions should explain the semantic
meaning of the term as reusable normalization vocabulary. Aliases may be empty when no stable alias is
supported by the input. Put machine-stable codes, statuses and relationships in
`taxonomy_proposal.taxonomy_core`; put labels, descriptions and aliases in `taxonomy_proposal.taxonomy_text`.
Put runtime semantic bindings in `taxonomy_proposal.semantic_binding`.

Promotion slots are taxonomy-defined runtime fields. Create them from the sample family itself, not from any
external preset. For field codes, set `promotion_slot` only when the field is a central document-level facet
for this document family: identity, date/time, party/actor, main object/topic, status/outcome, recurring
concept, or another value that is clearly useful for retrieval, filtering, display, grouping, or routing across
in-family documents. Do not promote a field merely because it is document-level.

Keep fields without promotion slots when they are useful extraction detail but not central runtime facets. Keep
row-native and section-local facts in row/cell or field vocabulary unless they also summarize a document-level
facet.

Define each slot in `taxonomy_core.promotion_slots`, then reference the slot code from
`field_codes[].promotion_slot`. Use null for fields that should remain normal extracted content only.

Use `single` for one best document-level value. Use `multi` for repeatable document-level facets such as
themes, characters, settings, named artifacts, recurring concepts, tags, parties, or other in-family values
that may naturally have more than one value per document. Promotion slot codes must be stable ASCII snake_case
and scoped to `document`.

Copy `sample_ids` from the input. Include `other` fallback terms and the exact `fallback_codes` object shown
in the output schema.

Return exactly one JSON object with schema_version `kernel.taxonomy_to_sample_analyses.v1`.
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
  "schema_version": "kernel.taxonomy_to_sample_analyses.v1",
  "source_schema_version": "kernel.sample_analyses.v1",
  "analysis_scope": "sample_set",
  "sample_ids": ["sample_001"],
  "target": {
    "update_state_contract": "kernel.create_taxonomy_update_state.input.v1"
  },
  "taxonomy_proposal": {
    "taxonomy_core": {
      "domains": [{"code": "candidate_domain", "status": "active", "parent_id": null}, {"code": "other", "status": "active", "parent_id": null}],
      "document_types": [{"code": "candidate_document_type", "status": "active", "domains": ["candidate_domain"], "allowed_categories": ["candidate_category", "other"], "allowed_subcategories": ["candidate_subcategory", "other"]}, {"code": "other", "status": "active", "domains": ["other"], "allowed_categories": ["other"], "allowed_subcategories": ["other"]}],
      "categories": [{"code": "candidate_category", "status": "active", "domains": ["candidate_domain"]}, {"code": "other", "status": "active", "domains": ["other"]}],
      "subcategories": [{"code": "candidate_subcategory", "status": "active", "parent_category": "candidate_category", "domains": ["candidate_domain"]}, {"code": "other", "status": "active", "parent_category": "other", "domains": ["other"]}],
      "field_codes": [{"code": "document_number", "status": "active", "value_type": "string", "domains": ["candidate_domain"], "promotion_slot": "document_number"}, {"code": "other", "status": "active", "value_type": "string", "domains": ["other"], "promotion_slot": null}],
      "row_types": [{"code": "candidate_row", "status": "active", "domains": ["candidate_domain"], "recommended_cell_codes": ["description", "amount"]}, {"code": "other", "status": "active", "domains": ["other"], "recommended_cell_codes": ["other"]}],
      "cell_codes": [{"code": "description", "status": "active", "value_type": "string", "domains": ["candidate_domain"]}, {"code": "amount", "status": "active", "value_type": "number_or_money_string", "domains": ["candidate_domain"]}, {"code": "other", "status": "active", "value_type": "string", "domains": ["other"]}],
      "promotion_slots": [{"slot": "document_number", "label": "Document Number", "description": "Stable document-level identifier when present.", "value_type": "string", "scope": "document", "cardinality": "single", "query_role": "primary", "display_rank": 10}],
      "fallback_codes": {"document_type": "other", "category": "other", "subcategory": "other", "field_code": "other", "row_type": "other", "cell_code": "other"}
    },
    "taxonomy_text": {
      "locale": "en",
      "terms": {
        "domains": [{"code": "candidate_domain", "label": "Candidate Domain", "description": "Broad semantic domain represented by the sample set.", "aliases": []}],
        "document_types": [{"code": "candidate_document_type", "label": "Candidate Document Type", "description": "Stable document type represented by the sample set.", "aliases": []}],
        "categories": [{"code": "candidate_category", "label": "Candidate Category", "description": "Reusable category supported by the sample set.", "aliases": []}],
        "subcategories": [{"code": "candidate_subcategory", "label": "Candidate Subcategory", "description": "Reusable subcategory under the candidate category.", "aliases": []}],
        "field_codes": [{"code": "document_number", "label": "Document Number", "description": "Reusable scalar identifier field.", "aliases": []}],
        "row_types": [{"code": "candidate_row", "label": "Candidate Row", "description": "Repeated row structure supported by the sample set.", "aliases": []}],
        "cell_codes": [{"code": "description", "label": "Description", "description": "Textual row description.", "aliases": []}, {"code": "amount", "label": "Amount", "description": "Numeric or monetary row amount.", "aliases": []}]
      }
    },
    "semantic_binding": {
      "field_codes": [{"code": "document_number", "promotion_slot": "document_number"}],
      "row_types": [{"code": "candidate_row", "binding_role": null}],
      "cell_codes": [{"code": "description", "binding_role": null}, {"code": "amount", "binding_role": null}]
    }
  },
  "validation": {"status": "passed", "open_decisions": [], "warnings": []},
  "quality": {"confidence": 0.0, "notes": []}
}
```

Kernel validation:
- Validate schema/source/scope/sample IDs, reject unknown properties and reject `taxonomy_proposal.taxonomy_id`.
- Require ASCII snake_case codes, no duplicates per taxonomy section and `other` fallback terms everywhere.
- Validate every domain/category/subcategory/cell/text/binding reference against `taxonomy_core`.
- Validate Promotion Slot definitions, field `promotion_slot` references and value types against the dynamic taxonomy registry.
- Build the custom taxonomy precursor from `taxonomy_core`, `taxonomy_text`, `semantic_binding` and Kernel policy.
- Do not copy `validation`, `quality`, `target` or artifact paths into the final taxonomy.
    """
).strip()
