"""Locale text source-authoring tool operations."""
from __future__ import annotations

from typing import Any

from . import locale_views, master_surface, profiles_surface
from .response import build_response
from .tools_values import find_term, package_and_locale, require_mapping, require_projection, required_text


def set_locale_text(project_root, payload: dict[str, Any]) -> dict[str, object]:
    package, locale = package_and_locale(project_root, payload)
    target_type = required_text(payload.get("target_type"), label="target_type")
    if target_type == "master_package":
        master = locale_views.clone_master_locale_payload(package, locale)
        master["description"] = required_text(payload.get("description"), label="description")
        value = master_surface.write_surface(project_root, master)
        return build_response("set_locale_text", value={"description": value["description"]}, required_fields=["target_type", "locale", "description"], locale=locale, locale_resolution={"locale": locale, "source": "explicit_locale"})
    if target_type == "master_term":
        return _set_master_term_text(project_root, package, locale, payload)
    return _set_projection_text(project_root, package, locale, payload)


def set_routing_lexicon(project_root, payload: dict[str, Any]) -> dict[str, object]:
    package, locale = package_and_locale(project_root, payload)
    profiles = locale_views.clone_profiles_locale_payload(package, locale)
    projection = require_projection(profiles["profiles"], required_text(payload.get("projection_id"), label="projection_id"))
    projection["text"]["routing_lexicon"] = require_mapping(payload.get("routing_lexicon"), label="routing_lexicon")
    value = profiles_surface.write_surface(project_root, profiles)
    return build_response(
        "set_routing_lexicon",
        value={"projection": value["profiles"][projection["projection_id"]]},
        required_fields=["projection_id", "locale", "routing_lexicon"],
        references_existing_codes=list(value["profiles"]),
        locale=locale,
        locale_resolution={"locale": locale, "source": "explicit_locale"},
    )


def _set_master_term_text(project_root, package: dict[str, Any], locale: str, payload: dict[str, Any]) -> dict[str, object]:
    master = locale_views.clone_master_locale_payload(package, locale)
    section_id = required_text(payload.get("section_id"), label="section_id")
    term_id = required_text(payload.get("term_id"), label="term_id")
    find_term(master, section_id, term_id)["text"] = require_mapping(payload.get("text"), label="text")
    value = master_surface.write_surface(project_root, master)
    return build_response(
        "set_locale_text",
        value={"term": find_term(value, section_id, term_id)},
        required_fields=["target_type", "locale", "section_id", "term_id", "text"],
        locale=locale,
        locale_resolution={"locale": locale, "source": "explicit_locale"},
    )


def _set_projection_text(project_root, package: dict[str, Any], locale: str, payload: dict[str, Any]) -> dict[str, object]:
    profiles = locale_views.clone_profiles_locale_payload(package, locale)
    projection = require_projection(profiles["profiles"], required_text(payload.get("projection_id"), label="projection_id"))
    text = require_mapping(payload.get("text"), label="text")
    projection["text"]["label"] = required_text(text.get("label"), label="text.label")
    projection["text"]["description"] = required_text(text.get("description"), label="text.description")
    projection["text"]["routing"] = require_mapping(text.get("routing"), label="text.routing")
    value = profiles_surface.write_surface(project_root, profiles)
    return build_response(
        "set_locale_text",
        value={"projection": value["profiles"][projection["projection_id"]]},
        required_fields=["target_type", "locale", "projection_id", "text"],
        references_existing_codes=list(value["profiles"]),
        locale=locale,
        locale_resolution={"locale": locale, "source": "explicit_locale"},
    )
