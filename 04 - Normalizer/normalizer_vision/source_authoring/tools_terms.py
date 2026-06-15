"""Master and projection source-authoring tool operations."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..taxonomy_sources import policy as source_policy
from . import master_surface, profiles_surface
from .metadata import MASTER_SECTION_LABELS
from .response import build_response
from .tools_values import find_term, require_list, require_mapping, require_projection, require_text_list, required_text


def create_release_package(project_root, payload: dict[str, Any]) -> dict[str, object]:
    from . import release_surface

    draft = dict(release_surface.read_surface(project_root))
    for field_name in ("release_id", "release_version", "default_authoring_locale", "default_runtime_locale"):
        if payload.get(field_name):
            draft[field_name] = required_text(payload.get(field_name), label=field_name)
    if payload.get("projection_ids") is not None:
        draft["projection_ids"] = require_text_list(payload.get("projection_ids"), label="projection_ids")
    if payload.get("available_locales") is not None:
        draft["available_locales"] = require_text_list(payload.get("available_locales"), label="available_locales")
    value = release_surface.write_surface(project_root, draft)
    return build_response("create_release_package", value=value, required_fields=["release_id", "release_version", "available_locales", "default_authoring_locale", "default_runtime_locale", "projection_ids"], references_existing_codes=value["projection_ids"])


def read_master_term(project_root, payload: dict[str, Any]) -> dict[str, object]:
    section_id = required_text(payload.get("section_id"), label="section_id")
    master = master_surface.read_surface(project_root)
    references = [item["term_id"] for item in require_list(master.get(section_id), label=section_id)]
    return build_response("read_master_term", value={"term": find_term(master, section_id, required_text(payload.get("term_id"), label="term_id"))}, allowed_values=list(MASTER_SECTION_LABELS), required_fields=["section_id", "term_id"], references_existing_codes=references)


def upsert_master_term(project_root, payload: dict[str, Any]) -> dict[str, object]:
    section_id = required_text(payload.get("section_id"), label="section_id")
    term_id = required_text(payload.get("term_id"), label="term_id")
    master = master_surface.read_surface(project_root)
    terms = list(master[section_id])
    item = {"term_id": term_id, "core": require_mapping(payload.get("core"), label="core"), "text": require_mapping(payload.get("text"), label="text")}
    for index, current in enumerate(terms):
        if current["term_id"] == term_id:
            terms[index] = item
            break
    else:
        terms.append(item)
    master[section_id] = terms
    value = master_surface.write_surface(project_root, master)
    return build_response("upsert_master_term", value={"term": find_term(value, section_id, term_id)}, required_fields=["section_id", "term_id", "core", "text"])


def retire_master_term(project_root, payload: dict[str, Any]) -> dict[str, object]:
    section_id = required_text(payload.get("section_id"), label="section_id")
    term_id = required_text(payload.get("term_id"), label="term_id")
    master = master_surface.read_surface(project_root)
    find_term(master, section_id, term_id)["core"]["status"] = "retired"
    value = master_surface.write_surface(project_root, master)
    return build_response("retire_master_term", value={"term": find_term(value, section_id, term_id)}, required_fields=["section_id", "term_id"], validation_risks=["retired_terms_must_remain_referenced"])


def read_projection(project_root, payload: dict[str, Any]) -> dict[str, object]:
    profiles = profiles_surface.read_surface(project_root)["profiles"]
    projection_id = required_text(payload.get("projection_id"), label="projection_id")
    return build_response("read_projection", value={"projection": require_projection(profiles, projection_id)}, required_fields=["projection_id"], references_existing_codes=list(profiles))


def upsert_projection(project_root, payload: dict[str, Any]) -> dict[str, object]:
    profiles = profiles_surface.read_surface(project_root)
    projection_id = required_text(payload.get("projection_id"), label="projection_id")
    current = profiles["profiles"].get(projection_id)
    if current is None:
        template_id = required_text(payload.get("template_projection_id"), label="template_projection_id")
        current = deepcopy(require_projection(profiles["profiles"], template_id))
    current["projection_id"] = projection_id
    current["core"] = require_mapping(payload.get("core"), label="core")
    profiles["profiles"][projection_id] = current
    ordered_ids = source_policy.canonical_projection_id_list(list(profiles["profiles"]), label="profiles")
    profiles["profiles"] = {item_id: profiles["profiles"][item_id] for item_id in ordered_ids}
    value = profiles_surface.write_surface(project_root, profiles)
    return build_response("upsert_projection", value={"projection": value["profiles"][projection_id]}, required_fields=["projection_id", "core"], references_existing_codes=list(value["profiles"]))
