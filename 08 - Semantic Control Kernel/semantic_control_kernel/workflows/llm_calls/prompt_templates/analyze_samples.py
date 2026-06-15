from __future__ import annotations

from textwrap import dedent


USER_PROMPT = dedent(
    """
You are the semantic sample-set analyzer for the Semantic Runtime Kernel.

You receive a JSON array of `kernel.analyze_sample.input.v1` objects. Analyze them as a set.

Goal:
- Identify the shared document family, stable semantic pattern, document structure, routing signals and useful taxonomy candidates.
- Derive compact but expressive candidate taxonomy codes for domains, document types, categories, subcategories, scalar fields, row types and cell codes.
- Derive one coherent candidate projection unless the samples clearly contain separate document contexts.
- Keep all candidate codes lowercase snake_case.
- Keep report-facing text substantive but short: normally one to three sentences per report field.
- Treat candidate codes as one global registry for the whole `taxonomy_seed`: every non-fallback code must be
  unique in `candidate_codes` and must define exactly one semantic meaning in exactly one taxonomy section.
- Codes are semantic identifiers, not local column labels. A code may be reused only when it means the same
  thing in the same semantic role across the sample set.
- When the same visible label, header, form field, row value, party attribute, section marker or repeated
  structure appears with different semantic roles, create distinct role-scoped codes. Scope by the observed
  role that makes the meaning different: party role, actor role, source/target side, section role, row/cell
  role, document side, time role, location role, amount basis, status role, or another stable in-family
  semantic context.
- Do not solve collisions by adding arbitrary numeric suffixes. If a distinct stable role is visible, encode
  that role in the code. If no distinct stable role is visible, keep one generic code and describe the
  ambiguity in the report instead of inventing duplicate vocabulary.
- If repeated wording is truly the same semantic concept, keep one code and treat the other wording as an
  alias or wording variant in the report text; do not emit duplicate codes.

Taxonomy design contract:
- `taxonomy_seed` is a controlled vocabulary for assigning future content from the same workflow to stable
  document, section, field, row and cell codes.
- Do not confuse narrow scope with sparse vocabulary.
- Narrow scope means staying inside the document family shown by the samples and avoiding broad neighboring
  document families or archive categories.
- Sufficient vocabulary means including enough codes to assign visible in-family structures and stable semantic
  distinctions without forcing routine content into `other`.
- Within the document family, preserve useful semantic depth: include all stable in-family distinctions when
  they are visible or structurally implied by the samples. Treat the taxonomy as a compact reference vocabulary
  for this particular family: it should teach later assignment steps what good and deep semantic coverage for
  this family looks like.
- Do not flatten distinct observed meanings into generic text or content codes merely to keep the vocabulary
  small.
- Compact means concise, reusable and non-duplicative; it does not mean the smallest possible vocabulary.
- Include a candidate term when it is one of:
  - `observed`: directly visible as a stable structure or semantic distinction in the samples.
  - `structurally_implied`: required to represent visible structure even if not named directly.
  - `near_boundary`: inside the same document family, close to visible patterns, and useful to avoid routine
    fallback to `other` for similar workflow inputs.
- Do not add a candidate term when it is:
  - a broad neighboring document family,
  - only a wording variant that should be an alias,
  - speculative archive expansion outside the sample family.
- Specialized terms are additive. Keep observed generic carrier codes when they are needed to assign visible
  structure, and add specialized codes beside them only when the distinction changes classification.
- Keep `taxonomy_seed.candidate_codes` synchronized with the seed vocabulary: each non-fallback code listed
  there must be defined in exactly one taxonomy_seed section. Use aliases for wording variants, and omit
  rejected ideas instead of listing them as candidate codes.
- Before returning JSON, check that every visible ordinary structure has a non-`other` code, no specialized term
  replaced a necessary generic carrier, all added terms remain inside the sample family, and the vocabulary is
  compact but expressive rather than sparse. Also ensure `candidate_codes` matches the codes actually defined
  in the taxonomy_seed sections plus fallback codes.

Construction rules:
- `sample_set` describes only shared or structurally relevant sample findings.
- `taxonomy_seed` is candidate vocabulary only, not a validated master taxonomy.
- `projection_seed` references codes from `taxonomy_seed` plus fallback `other` where useful.
- `projection_seed.projections[*].status` must be `draft`.
- Prefer one coherent projection when the samples fit one operational normalization context. Do not let that
  single projection flatten distinct materialization surfaces: identify document-level facets, normal scalar
  fields, repeated rows/cells, and section/clause/paragraph structures separately when they are visible or
  structurally implied.
- `promotion_rules` should cover the document-level fields or facets that make this document family useful at
  runtime: search, filtering, display, grouping, routing or later retrieval.
- Treat promotion candidates as one runtime surface, not the default destination for all useful facts. Propose
  promotion rules for central document-level retrieval, filtering, display, grouping, or routing facets. Keep
  incidental, subtype-only, section-local, or row-native values as fields or rows/cells.
- Use multi-value promotion candidates for repeatable facets that naturally have several values per document.
- Use empty arrays only when there is genuinely nothing to report.

Return valid JSON only.

Input:
{input_json}{validation_feedback_block}
    """
).strip()

OUTPUT_APPENDIX = dedent(
    """
Output structure:
```json
{
  "schema_version": "kernel.sample_analyses.v1",
  "analysis_scope": "sample_set",
  "input_contract": "kernel.analyze_sample.input.v1",
  "sample_set": {"sample_ids": ["sample_001"], "summary": "...", "document_family": "...", "shared_semantic_pattern": "...", "meaningful_variations": [], "classification": {"domain_codes": [], "document_type_codes": [], "category_codes": [], "subcategory_codes": [], "confidence": 0.0}, "structure": {"shape": "mixed", "section_roles": [], "party_roles": []}, "signals": {"labels": [], "text_markers": []}},
  "taxonomy_seed": {
    "candidate_codes": ["candidate_domain", "candidate_document_type", "other"],
    "domains": [{"code": "candidate_domain", "label": "...", "description": "..."}],
    "document_types": [{"code": "candidate_document_type", "label": "...", "description": "...", "domains": ["candidate_domain"], "allowed_categories": ["other"], "allowed_subcategories": ["other"]}],
    "categories": [], "subcategories": [], "field_codes": [], "row_types": [], "cell_codes": [],
    "fallback_codes": {"document_type": "other", "category": "other", "subcategory": "other", "field_code": "other", "row_type": "other", "cell_code": "other"}
  },
  "projection_seed": {
    "candidate_projection_ids": ["candidate_domain.custom.v1"],
    "projections": [{"projection_id": "candidate_domain.custom.v1", "status": "draft", "label": "...", "description": "...", "domain_ids": ["candidate_domain"], "include_document_types": ["candidate_document_type", "other"], "include_categories": ["other"], "include_subcategories": ["other"], "include_field_codes": ["other"], "include_row_types": ["other"], "include_cell_codes": ["other"], "promotion_rules": [], "routing": {"when_to_use": "...", "avoid_when": "...", "example_document_types": ["candidate_document_type"], "section_roles": ["other"], "party_roles": ["other"]}, "routing_lexicon": {"text_markers": [], "domain_markers": []}}]
  },
  "user_report_samples_seed": {"report_purpose": "...", "overview": "...", "taxonomy_view": {"domain_findings": "...", "document_type_findings": "...", "category_findings": "...", "field_code_findings": "...", "row_and_cell_findings": "...", "taxonomy_gaps_or_decisions": []}, "projection_view": {"projection_boundary_findings": "...", "included_semantics": "...", "routing_findings": "...", "promotion_rule_findings": "...", "split_or_merge_considerations": "...", "projection_gaps_or_decisions": []}, "sample_set_findings": {"what_the_samples_show_together": "...", "taxonomy_relevance": "...", "projection_relevance": "..."}, "recommended_user_decisions": [], "report_risks_or_uncertainties": []},
  "quality": {"confidence": 0.0, "notes": []}
}
```
- `sample_set.structure.shape` must be one of: `text`, `form`, `table`, `form_with_table`, `list`, `mixed`.
- Keep `candidate_codes` synchronized with taxonomy sections and fallbacks.
- `projection_seed` may only reference codes from `taxonomy_seed` plus `other`.
- `user_report_samples_seed` must stay grounded in `sample_set`, `taxonomy_seed` and `projection_seed`.
    """
).strip()
