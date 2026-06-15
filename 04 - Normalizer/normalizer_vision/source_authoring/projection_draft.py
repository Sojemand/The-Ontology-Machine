"""One-step draft creation for projection core, routing text, and lexicon."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..taxonomy_sources import policy as source_policy
from . import adapter, locale_views
from .draft_package import ensure_projection_clone
from .projection_draft_text import apply_text_draft, generated_files, mirror_draft_text_to_other_locales
from .projection_draft_values import (
    TOP_LEVEL_COVERAGE_FIELDS,
    first_present,
    optional_mapping,
    optional_string_list,
    require_bool,
    require_mapping,
    required_projection_id,
    required_string_list,
)
from .response import build_response


def create_projection_draft(project_root, payload: dict[str, Any]) -> dict[str, object]:
    context = adapter.load_context(project_root)
    package = deepcopy(context["package"])
    projection_id = required_projection_id(payload.get("projection_id"), label="projection_id")
    template_projection_id = required_projection_id(payload.get("template_projection_id"), label="template_projection_id")
    locale = source_policy.require_locale(payload.get("locale"), label="locale")
    if locale not in set(locale_views.available_locales(package)):
        raise ValueError(f"locale ist im Source-Paket nicht vorhanden: {locale}")
    overwrite_existing = require_bool(payload.get("overwrite_existing", False), label="overwrite_existing")
    if template_projection_id not in package["projections"]:
        raise ValueError(f"template_projection_id ist unbekannt: {template_projection_id}")

    created_new_projection = projection_id not in package["projections"]
    if created_new_projection:
        _require_explicit_coverage_fields(payload)
        ensure_projection_clone(package, template_projection_id, projection_id)
    elif not overwrite_existing:
        raise ValueError(f"projection_id existiert bereits: {projection_id}. overwrite_existing=true ist erforderlich.")
    elif projection_id != template_projection_id:
        package["projections"][projection_id] = deepcopy(package["projections"][template_projection_id])

    projection = package["projections"][projection_id]
    projection["core"]["projection_id"] = projection_id
    active_text = require_mapping(projection["texts"].get(locale), label=f"{projection_id}.texts.{locale}")
    template_lexicon = deepcopy(active_text.get("routing_lexicon") or {})
    _apply_core_draft(projection["core"], payload)
    apply_text_draft(active_text, payload, domain_ids=list(projection["core"]["domain_ids"]), template_lexicon=template_lexicon)
    available_locales = locale_views.available_locales(package)
    if created_new_projection:
        mirror_draft_text_to_other_locales(projection, payload, active_locale=locale, domain_ids=list(projection["core"]["domain_ids"]), available_locales=available_locales)

    saved = adapter.save_context(project_root, package, materialization_version=context["materialization_version"])
    locale_payload = locale_views.clone_profiles_locale_payload(saved, locale)
    return build_response(
        "create_projection_draft",
        value={"projection": locale_payload["profiles"][projection_id]},
        required_fields=["projection_id", "template_projection_id", "locale", "label", "description", "when_to_use", "avoid_when", "example_document_types", *TOP_LEVEL_COVERAGE_FIELDS],
        references_existing_codes=saved["release"]["projection_ids"],
        locale=locale,
        locale_resolution={"locale": locale, "source": "explicit_locale"},
        created_new_projection=created_new_projection,
        generated_files=generated_files(projection_id, available_locales),
        provenance={"operation": "create_projection_draft", "projection_id": projection_id, "template_projection_id": template_projection_id, "locale": locale, "source": "explicit_projection_draft_inputs"},
        validation_risks=[
            "Compile and export are still required before the new prompt-visible routing guidance becomes active.",
            "New draft projections should be reviewed for coverage and locale text quality before release.",
            *(["New projection text was mirrored to all available locales to avoid stale template labels."] if created_new_projection and len(available_locales) > 1 else []),
        ],
        compile_effect="The projection draft updates source-layer projection core and locale text only; later compile/export reads directly from that saved source state.",
        prompt_effect="The saved draft changes future projection catalog guidance and routing signals after compile or export.",
        corpus_effect="The new projection becomes corpus-visible only after compile, export, and activation.",
    )


def _apply_core_draft(core: dict[str, Any], payload: dict[str, Any]) -> None:
    for field_name in TOP_LEVEL_COVERAGE_FIELDS:
        values = optional_string_list(payload.get(field_name), label=field_name)
        if values is not None:
            core[field_name] = values
    routing_payload = optional_mapping(payload.get("routing"), label="routing")
    example_document_types = required_string_list(first_present(payload, routing_payload, "example_document_types"), label="example_document_types")
    core["routing"]["example_document_types"] = example_document_types
    core["include_document_types"] = _merge_unique(list(core["include_document_types"]), example_document_types)
    for field_name in ("section_roles", "party_roles"):
        values = optional_string_list(first_present(payload, routing_payload, field_name), label=field_name)
        if values is not None:
            core["routing"][field_name] = values
    if not list(core.get("domain_ids") or []):
        raise ValueError("domain_ids duerfen nicht leer sein.")


def _require_explicit_coverage_fields(payload: dict[str, Any]) -> None:
    missing = [field_name for field_name in TOP_LEVEL_COVERAGE_FIELDS if payload.get(field_name) in (None, "")]
    if missing:
        raise ValueError("Neue Projections muessen explizite Coverage-Felder setzen, damit keine Template-Reste aktiv bleiben: " + ", ".join(missing))


def _merge_unique(existing: list[str], additions: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in [*existing, *additions]:
        token = str(item).strip()
        if not token or token in seen:
            continue
        seen.add(token)
        result.append(token)
    return result
