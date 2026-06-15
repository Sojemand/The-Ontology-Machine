"""Path-stable facade for source-layer authoring tools."""
from __future__ import annotations

from typing import Any

from . import adapter, locale_views, master_surface, profiles_surface, release_surface
from .metadata import MASTER_SECTION_LABELS
from .projection_draft import create_projection_draft
from .response import build_response
from .tools_locale import set_locale_text, set_routing_lexicon
from .tools_terms import (
    create_release_package,
    read_master_term,
    read_projection,
    retire_master_term,
    upsert_master_term,
    upsert_projection,
)


def dispatch(action: str, payload: dict[str, Any], *, project_root) -> dict[str, object]:
    if action == "create_release_package":
        return create_release_package(project_root, payload)
    if action == "read_release_package":
        value = release_surface.read_surface(project_root)
        return build_response(action, value=value, required_fields=["release_id", "release_version", "available_locales", "default_authoring_locale", "default_runtime_locale", "projection_ids"], references_existing_codes=value["projection_ids"])
    if action == "read_translation_glossary_locale":
        context = adapter.load_context(project_root)
        package = context["package"]
        locale = _required_locale(payload, package)
        return build_response(
            action,
            value=locale_views.clone_glossary_locale_payload(package, locale),
            allowed_values=locale_views.available_locales(package),
            required_fields=["locale"],
        )
    if action == "list_master_terms":
        master = master_surface.read_surface(project_root)
        terms = [{"section_id": section_id, "term_id": item["term_id"], "label": item["text"].get("label", "")} for section_id in MASTER_SECTION_LABELS for item in master[section_id]]
        return build_response(action, value={"terms": terms}, allowed_values=list(MASTER_SECTION_LABELS))
    if action == "read_master_term":
        return read_master_term(project_root, payload)
    if action == "upsert_master_term":
        return upsert_master_term(project_root, payload)
    if action == "retire_master_term":
        return retire_master_term(project_root, payload)
    if action == "list_projections":
        profiles = profiles_surface.read_surface(project_root)["profiles"]
        items = [{"projection_id": projection_id, "label": item["text"].get("label", "")} for projection_id, item in profiles.items()]
        return build_response(action, value={"projections": items}, references_existing_codes=list(profiles))
    if action == "read_projection":
        return read_projection(project_root, payload)
    if action == "create_projection_draft":
        return create_projection_draft(project_root, payload)
    if action == "upsert_projection":
        return upsert_projection(project_root, payload)
    if action == "set_locale_text":
        return set_locale_text(project_root, payload)
    if action == "set_routing_lexicon":
        return set_routing_lexicon(project_root, payload)
    raise ValueError(f"Unbekannte Source-Operation: {action}")


def _required_locale(payload: dict[str, Any], package: dict[str, Any]) -> str:
    locale = str(payload.get("locale") or "").strip().replace("_", "-").casefold()
    if not locale:
        raise ValueError("locale fehlt.")
    if locale not in set(locale_views.available_locales(package)):
        raise ValueError(f"Unbekannte Locale: {locale}")
    return locale
