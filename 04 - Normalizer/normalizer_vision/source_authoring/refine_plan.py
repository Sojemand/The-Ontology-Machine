"""Data-informed planning shared by review and apply actions."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from ..document_io import load_structured_document
from ..models.serialization import load_json
from . import locale_views
from .draft_ids import build_lookup, derive_projection_id, derive_term_id, existing_term, projection_id_hint
from .draft_package import ensure_master_term, ensure_projection_clone, ensure_projection_include, master_templates, merge_routing_markers, section_for_phrase, update_projection_text
from .impact_preview import describe_package_delta
from .review_support import compact_ranking, excerpt_text, flatten_strings, load_review_context, normalize_text, select_review_projection


def build_refine_plan(project_root, payload: dict[str, Any]) -> dict[str, object]:
    structured_path = _required_path(payload.get("structured_sample_path"), label="structured_sample_path")
    normalized_path = _required_path(payload.get("expected_normalized_path"), label="expected_normalized_path")
    original_reference_path = _optional_path(payload.get("original_reference_path"))
    sample_label = str(payload.get("sample_label") or structured_path.name).strip() or structured_path.name
    context = load_review_context(project_root)
    lookup = build_lookup(context["package"])
    templates = master_templates(context["package"])
    structured = load_structured_document(structured_path, max_bytes=context["config"].max_structured_bytes).payload
    normalized = _require_mapping(load_json(normalized_path), label="expected_normalized_path")
    selection, ranking = select_review_projection(context, structured)
    candidate = deepcopy(context["package"])
    requested_projection = str(((normalized.get("projection") or {}).get("projection_id") or "")).strip()
    target_projection_id, warnings, applied_changes = _target_projection(candidate, lookup, sample_label, structured, normalized, selection.profile.projection_id, requested_projection, ranking)
    projection_suggestions, master_suggestions = _apply_codes(candidate, lookup, templates, target_projection_id, normalized, applied_changes)
    markers = merge_routing_markers(candidate, target_projection_id, (structured.get("content") or {}).get("free_text", ""), (structured.get("context") or {}).get("document_title", ""), (structured.get("context") or {}).get("description", ""), limit=6)
    if markers:
        applied_changes.append({"action": "update_routing_lexicon", "target": target_projection_id, "reason": f"{len(markers)} routing markers from the structured sample were added."})
    impact = describe_package_delta(project_root, candidate, materialization_version=context["release_preview"]["materialization_version"])
    warnings.extend(_warnings(structured, normalized, ranking, projection_suggestions, master_suggestions))
    review_payload = {
        "review_mode": "data_informed",
        "language_policy": {
            "available_locales": list(candidate["release"]["available_locales"]),
            "default_authoring_locale": candidate["release"]["default_authoring_locale"],
            "document_scope": "Locale-aware source package",
        },
        "input_summary": {"sample_label": sample_label, "structured_sample_path": str(structured_path), "expected_normalized_path": str(normalized_path), "original_reference_path": str(original_reference_path) if original_reference_path else ""},
        "release_summary": {"release_id": context["release_preview"]["release_id"], "release_version": context["release_preview"]["release_version"], "candidate_fingerprint": impact["candidate_release_fingerprint"], "projection_count": len(candidate["release"]["projection_ids"])},
        "projection_suggestions": projection_suggestions,
        "master_term_suggestions": master_suggestions,
        "routing_review": {"selected_projection_id": target_projection_id, "selected_reason": selection.reason, "candidate_rankings": compact_ranking(ranking), "warnings": warnings},
        "document_comparison": _document_comparison(structured, normalized, original_reference_path),
        "information_balance": _information_balance(structured, normalized),
        "warnings": warnings,
        "next_steps": _next_steps(projection_suggestions, master_suggestions),
    }
    return {"candidate_package": candidate, "review_payload": review_payload, "applied_changes": applied_changes, "impact": impact, "references": list(candidate["release"]["projection_ids"])}


def _target_projection(candidate: dict[str, Any], lookup: dict[str, dict[str, str]], sample_label: str, structured: dict[str, Any], normalized: dict[str, Any], selected_projection_id: str, requested_projection: str, ranking: list[dict[str, Any]]) -> tuple[str, list[str], list[dict[str, str]]]:
    warnings, changes = [], []
    target_projection_id = requested_projection or selected_projection_id
    if requested_projection and requested_projection not in candidate["projections"]:
        projection = projection_id_hint(requested_projection)
        ensure_projection_clone(candidate, selected_projection_id, projection["projection_id"])
        target_projection_id = projection["projection_id"]
        update_projection_text(candidate, target_projection_id, label=f"Draft projection for {sample_label}", description="Autogenerated draft projection derived from the expected normalized sample.", when_to_use=f"When sample '{sample_label}' matches this projection.", avoid_when="Review coverage before release.")
        changes.append({"action": "clone_projection", "target": target_projection_id, "source": selected_projection_id, "reason": f"Projection '{requested_projection}' war noch nicht vorhanden und wurde als Draft angelegt."})
        if projection["requires_id_review"]:
            warnings.append(f"Projection-ID '{target_projection_id}' wurde heuristisch normalisiert und braucht Review.")
    elif not requested_projection and (not ranking or int(ranking[0]["score"]) <= 0):
        derived = derive_projection_id(candidate, lookup, sample_label, selected_projection_id)
        ensure_projection_clone(candidate, selected_projection_id, derived["projection_id"])
        target_projection_id = derived["projection_id"]
        update_projection_text(candidate, target_projection_id, label=f"Draft projection for {sample_label}", description="Autogenerated draft projection derived from sample and expected normalized output.", when_to_use=excerpt_text((structured.get("content") or {}).get("free_text"), limit=160), avoid_when="Review coverage before release.")
        changes.append({"action": "clone_projection", "target": target_projection_id, "source": selected_projection_id, "reason": "Bestehende Projection deckt das Sample noch nicht tragfaehig ab."})
        if derived["requires_id_review"]:
            warnings.append(f"Neue Projection-ID '{target_projection_id}' braucht Review.")
    else:
        changes.append({"action": "reuse_projection", "target": target_projection_id, "reason": "Bestehende Projection wird aus dem erwarteten Normalisat weiter verfeinert."})
    return target_projection_id, warnings, changes


def _apply_codes(candidate: dict[str, Any], lookup: dict[str, dict[str, str]], templates: dict[str, dict[str, Any]], projection_id: str, normalized: dict[str, Any], applied_changes: list[dict[str, str]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    projection_suggestions: list[dict[str, object]] = []
    master_suggestions: list[dict[str, object]] = []
    active_locale = locale_views.default_authoring_locale(candidate)
    for section_id, codes in _normalized_codes(normalized).items():
        for code in sorted(codes):
            current = existing_term(candidate, lookup, code)
            if current is not None:
                _, term_id = current
                if ensure_projection_include(candidate, projection_id, section_id, term_id):
                    applied_changes.append({"action": "extend_projection", "target": projection_id, "reason": f"Bestehender Code '{term_id}' wurde aus dem erwarteten Normalisat uebernommen."})
                    projection_suggestions.append({"projection_id": projection_id, "label": term_id, "action": "extend_projection", "reason": f"Bekannter Code '{term_id}' fehlte in der Projection."})
                continue
            derived = derive_term_id(candidate, lookup, section_id, code)
            if ensure_master_term(candidate, templates, section_id, derived["term_id"], projection_id, phrase=code, origin="Data-Informed"):
                applied_changes.append({"action": "create_master_term", "target": f"{section_id}.{derived['term_id']}", "reason": f"Neuer Draft-Code fuer '{code}' aus dem erwarteten Normalisat angelegt."})
            ensure_projection_include(candidate, projection_id, section_id, derived["term_id"])
            applied_changes.append({"action": "extend_projection", "target": projection_id, "reason": f"Neuer Draft-Code '{derived['term_id']}' wurde in die Projection aufgenommen."})
            master_suggestions.append({"section_id": section_id, "term_id": derived["term_id"], "label": code, "suggestion_type": "new", "reason": f"Code '{code}' war im Master noch nicht vorhanden und wurde als Draft angelegt."})
    projection_suggestions.insert(0, {"projection_id": projection_id, "label": candidate["projections"][projection_id]["texts"][active_locale]["label"], "recommended": True, "action": "reuse_with_review", "reason": "Diese Projection ist der aktive Draft-Zielzustand."})
    return projection_suggestions, master_suggestions


def _normalized_codes(payload: dict[str, Any]) -> dict[str, set[str]]:
    classification = payload.get("classification") or {}
    content = payload.get("content") or {}
    return {
        "document_types": {str(classification.get("document_type") or "").strip()} - {""},
        "categories": {str(classification.get("category") or "").strip()} - {""},
        "subcategories": {str(classification.get("subcategory") or "").strip()} - {""},
        "field_codes": {str(key).strip() for key in ((content.get("fields") or {})) if str(key).strip()},
        "row_types": {str(item.get("_row_type") or "").strip() for item in (content.get("rows") or []) if isinstance(item, dict) and str(item.get("_row_type") or "").strip()},
        "cell_codes": {str(key).strip() for key in (content.get("structure") or {}).get("columns", []) if str(key).strip()} | {str(key).strip() for item in (content.get("rows") or []) if isinstance(item, dict) for key in item if not str(key).startswith("_") and str(key).strip()},
    }


def _document_comparison(structured: dict[str, Any], normalized: dict[str, Any], original_reference_path: Path | None) -> dict[str, dict[str, object]]:
    return {"original": {"status": "provided" if original_reference_path else "missing", "path": str(original_reference_path) if original_reference_path else "", "summary": "Nur Referenzpfad; die Review-Analyse basiert auf structured und erwartetem normalized."}, "structured": {"status": "loaded", "summary": {"document_type": ((structured.get("classification") or {}).get("document_type") or ""), "category": ((structured.get("classification") or {}).get("category") or ""), "field_keys": sorted(((structured.get("content") or {}).get("fields") or {}).keys()), "row_types": sorted(item.get("_row_type", "") for item in ((structured.get("content") or {}).get("rows") or []) if isinstance(item, dict)), "free_text_excerpt": excerpt_text((structured.get("content") or {}).get("free_text"))}}, "normalized": {"status": "loaded", "summary": {"projection_id": ((normalized.get("projection") or {}).get("projection_id") or ""), "document_type": ((normalized.get("classification") or {}).get("document_type") or ""), "field_keys": sorted(_normalized_codes(normalized)["field_codes"]), "row_types": sorted(_normalized_codes(normalized)["row_types"]), "cell_keys": sorted(_normalized_codes(normalized)["cell_codes"]), "notes": list(((normalized.get("context") or {}).get("normalization_notes") or []))[:4]}}}


def _information_balance(structured: dict[str, Any], normalized: dict[str, Any]) -> dict[str, list[str]]:
    structured_tokens = {normalize_text(item) for item in flatten_strings(structured)}
    normalized_tokens = {normalize_text(item) for item in flatten_strings(normalized)}
    kept = [item for item in sorted(_normalized_codes(normalized)["field_codes"] | _normalized_codes(normalized)["row_types"] | _normalized_codes(normalized)["cell_codes"]) if normalize_text(item) in normalized_tokens]
    condensed = []
    raw_doc_type = ((structured.get("classification") or {}).get("document_type") or "")
    normalized_doc_type = ((normalized.get("classification") or {}).get("document_type") or "")
    if raw_doc_type and normalized_doc_type and normalize_text(raw_doc_type) != normalize_text(normalized_doc_type):
        condensed.append(f"document_type: {raw_doc_type} -> {normalized_doc_type}")
    lost = [token for token in sorted(structured_tokens) if token and len(token) > 4 and token not in normalized_tokens][:6]
    return {"kept": kept[:6], "condensed": condensed[:6], "lost": lost}


def _warnings(structured: dict[str, Any], normalized: dict[str, Any], ranking: list[dict[str, Any]], projection_suggestions: list[dict[str, object]], master_suggestions: list[dict[str, object]]) -> list[str]:
    warnings = []
    if ranking and int(ranking[0]["score"]) <= 0:
        warnings.append("Routing-Lexika liefern fuer dieses Sample kaum belastbare Treffer.")
    if len(ranking) > 1 and int(ranking[0]["score"]) - int(ranking[1]["score"]) <= 1:
        warnings.append("Mehrere Projections liegen dicht beieinander; Routing-Entscheidung sollte manuell geprueft werden.")
    if len(projection_suggestions) > 1:
        warnings.append("Die gewaehlte Projection musste in ihrer Fachabdeckung erweitert werden.")
    if master_suggestions:
        warnings.append("Das erwartete Normalisat enthaelt Codes, die im aktuellen Master noch fehlten und als Draft angelegt wurden.")
    if not ((normalized.get("projection") or {}).get("selection") or {}).get("reason"):
        warnings.append("Das erwartete Normalisat enthaelt keine sichtbare projection.selection.reason.")
    return warnings


def _next_steps(projection_suggestions: list[dict[str, object]], master_suggestions: list[dict[str, object]]) -> list[str]:
    steps = ["Draft gegen structured und erwartetes Normalisat fachlich pruefen."]
    if len(projection_suggestions) > 1:
        steps.append("Projection-Coverage fuer die neu uebernommenen Codes in Taxonomy Profiles nachschaerfen.")
    if master_suggestions:
        steps.append("Neue Draft-Begriffe im Taxonomy Master mit belastbaren englischen Control-Labels und Beschreibungen vervollstaendigen.")
    steps.append("Danach `preview_impact`, `validate_release_package` und `compile_release_package` ausfuehren.")
    return steps


def _required_path(value: Any, *, label: str) -> Path:
    path = Path(str(value or "")).expanduser()
    if not str(path).strip():
        raise ValueError(f"{label} muss ein Pfad sein.")
    if not path.exists() or not path.is_file():
        raise ValueError(f"{label} wurde nicht gefunden: {path}")
    return path


def _optional_path(value: Any) -> Path | None:
    if value in (None, ""):
        return None
    path = Path(str(value)).expanduser()
    return path if str(path).strip() else None


def _require_mapping(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} muss ein JSON-Objekt liefern.")
    return value
