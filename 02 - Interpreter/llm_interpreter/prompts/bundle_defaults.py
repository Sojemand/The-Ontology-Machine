"""Default prompt-bundle texts for the vision interpreter."""
from __future__ import annotations

USER_PROMPT_RULES_MD = """\
Work vision-first. The image is primary evidence; OCR raw blocks are secondary evidence.
Build the final structure from your own synthesis of visible page content plus OCR raw blocks.
Derive semantic segments, fields, rows, and functions yourself from low-level evidence and image content.
OCR raw blocks may be low-level OCR/layout blocks with type, layout_label, value, position, formatting, or HTML-like <table> text only.
Do not expect prebuilt summaries, facts, tables, sections, semantic roles, document types, or field labels in the raw input.
Parse HTML-like tables as evidence, but verify them against the image.
Correct OCR errors. Use only confirmed or visually corrected data.
content.free_text must be corrected full text in reading order, not the raw OCR dump.
Required: every value in context, content.fields, and content.rows must appear verbatim as a substring in content.free_text. Same spelling, same format. No ISO date when free_text has a prose date. No integers when free_text has thousands separators. No composed values with separators.
Insert vision-only values into content.free_text before using them as field values.
Keys, classifications, and structure codes do not need to appear in free_text; extracted values do.
Additional fields are allowed only in context, content.fields, and row objects."""

BORN_DIGITAL_USER_PROMPT_RULES_MD = """\
Work raw-first for born-digital/file artifacts. Use the page-scoped raw blocks as the primary textual source.
Use the visible page image only to verify structure, resolve conflicts, or correct visibly broken raw text.
Raw section order is not authoritative on multi-column pages. Use raw blocks for wording evidence, but reconstruct reading order from the visible column layout: finish one column top-to-bottom before moving to the next, unless visible cues clearly indicate another order.
If raw blocks look column-mixed and reliable full reconstruction is uncertain or too costly, return a compact high-signal extraction, set needs_review=true, and mention column-mixed raw order in review_reason.
The raw reference may contain only low-level blocks with type, layout_label, value, position, formatting, origin, or HTML-like <table> text.
Do not expect precomputed summaries, facts, tables, sections, semantic roles, document types, or field labels in the raw.
Derive semantic segments, fields, rows, and functions yourself from the low-level evidence.
Treat raw blocks as evidence units, not as final semantic units.
Split raw sections into separate segments when the local semantic act changes, especially at speaker changes, question/answer boundaries, heading/body boundaries, or narration/direct speech boundaries.
Prefer specific unit_kind labels over generic paragraph labels whenever the local text supports it.
Add function when a clear local semantic role is visible. Keep unit_kind as the stable segment class and use function for the segment's local meaning.
content.free_text is only a short keyword-style summary for the visible page. Do NOT reproduce the full visible text there.
The full semantic summary is built later downstream; keep content.free_text brief or null.
Return valid JSON only.
Follow the required schema exactly."""

SCAN_USER_PROMPT_RULES_MD = """\
Work image-first for scan/image artifacts. Treat OCR raw blocks as secondary and fallible.
Use the visible page image as the primary source. Only adopt OCR text when it is visually supported or clearly corrected by the image.
OCR raw blocks may be only low-level OCR/layout blocks with type, layout_label, value, position, formatting, or HTML-like <table> text.
Do not expect precomputed summaries, facts, tables, sections, semantic roles, document types, or field labels in the raw.
Derive semantic segments, fields, rows, and functions yourself from the low-level evidence and the visible page image.
Parse HTML-like tables as evidence, but verify them against the visible page image.
content.free_text must be a corrected full text in reading order, not the raw OCR dump.
If a value is only visible in the image, insert it into content.free_text before using it in fields or rows.
Return valid JSON only.
Follow the required schema exactly."""

PROJECTION_HINT_POLICY_MD = """\
Projection hint rules:
- context.projection_hint is optional.
- If nothing clearly fits, omit context.projection_hint completely.
- If you set context.projection_hint, use exactly these fields:
  projection_id (catalog string), confidence (number), reason (string), matched_signals (string[]).
- Use projection_hint as an advisory routing hint from your document understanding, not as an OCR copy.
- If the catalog names a control locale, map classification terms, the routing decision, reason, and matched_signals into that catalog language; evidence values stay in the document language.
- Use reason and matched_signals only for real document-based signals.
Valid example:
"projection_hint": {"projection_id": "finance.default.v1", "confidence": 0.71, "reason": "An invoice, invoice number, and total amount are visible.", "matched_signals": ["invoice", "invoice number", "total amount"]}
Example without hint:
"context": {}"""


def resolve_user_prompt_rules(*, is_file_profile: bool, is_scan: bool, configured_text: str | None = None) -> str:
    normalized = str(configured_text or "").strip()
    if not is_file_profile:
        return normalized or USER_PROMPT_RULES_MD
    if is_scan:
        return SCAN_USER_PROMPT_RULES_MD
    if not normalized or normalized in {
        USER_PROMPT_RULES_MD.strip(),
        BORN_DIGITAL_USER_PROMPT_RULES_MD.strip(),
        SCAN_USER_PROMPT_RULES_MD.strip(),
    }:
        return BORN_DIGITAL_USER_PROMPT_RULES_MD
    return normalized


__all__ = [
    "BORN_DIGITAL_USER_PROMPT_RULES_MD",
    "PROJECTION_HINT_POLICY_MD",
    "SCAN_USER_PROMPT_RULES_MD",
    "USER_PROMPT_RULES_MD",
    "resolve_user_prompt_rules",
]
