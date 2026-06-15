"""Create a small source package for one special-purpose archive."""
from __future__ import annotations

from typing import Any

from ..taxonomy_sources import policy as source_policy
from . import adapter
from .minimal_custom_master import master_core, master_text
from .minimal_custom_projection import projection_core
from .minimal_custom_values import (
    derive_markers,
    generated_files,
    required_text,
    single_term,
    stable_id,
    string_list,
    term_list,
)
from .response import build_response


def create_minimal_custom_release(project_root, payload: dict[str, Any]) -> dict[str, object]:
    context = adapter.load_context(project_root)
    current_release = context["package"]["release"]
    locale = source_policy.require_locale(payload.get("language"), label="language")
    release_id = stable_id(payload.get("release_id") or current_release["release_id"], label="release_id")
    release_version = required_text(payload.get("release_version") or current_release["release_version"], label="release_version")
    projection_id = stable_id(payload.get("projection_id"), label="projection_id")
    archive_label = required_text(payload.get("archive_label"), label="archive_label")
    archive_description = required_text(payload.get("archive_description"), label="archive_description")

    domain = single_term(payload.get("domain"), default_code="custom", default_label=archive_label, default_description=archive_description)
    category = single_term(payload.get("category"), default_code=domain["code"], default_label=archive_label, default_description=archive_description)
    subcategory = single_term(payload.get("subcategory"), default_code="special_archive", default_label=archive_label, default_description=archive_description)
    document_types = term_list(payload.get("document_types"), label="document_types", require_items=True)
    field_codes = term_list(payload.get("field_codes"), label="field_codes", require_items=True)
    row_types = term_list(payload.get("row_types"), label="row_types", require_items=False)
    cell_codes = term_list(payload.get("cell_codes"), label="cell_codes", require_items=False)
    text_markers = string_list(payload.get("text_markers"), label="text_markers", required=False)
    if not text_markers:
        text_markers = derive_markers(archive_label, archive_description, *[item["label"] for item in document_types], *[item["label"] for item in field_codes])
    if not text_markers:
        raise ValueError("text_markers duerfen fuer ein Custom Release nicht leer sein.")

    package = _package_payload(
        release_id=release_id,
        release_version=release_version,
        locale=locale,
        projection_id=projection_id,
        archive_label=archive_label,
        archive_description=archive_description,
        domain=domain,
        category=category,
        subcategory=subcategory,
        document_types=document_types,
        field_codes=field_codes,
        row_types=row_types,
        cell_codes=cell_codes,
        text_markers=text_markers,
        payload=payload,
    )
    saved = adapter.save_context(project_root, package, materialization_version=context["materialization_version"])
    counts = _term_counts(saved)
    return build_response(
        "create_minimal_custom_release",
        headline="Minimal custom release saved",
        summary_lines=[
            f"Release: {release_id}",
            f"Projection: {projection_id}",
            f"Runtime locale: {locale}",
            f"Custom terms: {sum(counts.values()) - counts['projections']}",
        ],
        required_fields=["language", "projection_id", "archive_label", "archive_description", "document_types", "field_codes"],
        references_existing_codes=saved["release"]["projection_ids"],
        value={"release": saved["release"], "term_counts": counts},
        locale=locale,
        projection_ids=saved["release"]["projection_ids"],
        generated_files=generated_files(projection_id, [locale]),
        provenance={"operation": "create_minimal_custom_release", "source": "explicit_agent_authored_custom_taxonomy"},
        validation_risks=[
            "This replaces the active working extraction pack with a small custom package.",
            "The custom terms should be based on inspected sample content and reviewed before activation.",
        ],
        compile_effect="The active source package now contains only the custom master terms and projection.",
        prompt_effect="After compile/export, routing guidance and field labels come from the custom package, not the default master taxonomy.",
        corpus_effect="No existing DB changes until the release is exported and activated.",
    )


def _package_payload(**kwargs) -> dict[str, Any]:
    domain = kwargs["domain"]
    category = kwargs["category"]
    subcategory = kwargs["subcategory"]
    projection_id = kwargs["projection_id"]
    locale = kwargs["locale"]
    document_types = kwargs["document_types"]
    field_codes = kwargs["field_codes"]
    row_types = kwargs["row_types"]
    cell_codes = kwargs["cell_codes"]
    return {
        "release": {
            "release_id": kwargs["release_id"],
            "release_version": kwargs["release_version"],
            "available_locales": [locale],
            "default_authoring_locale": locale,
            "default_runtime_locale": locale,
            "projection_ids": [projection_id],
            "governance": {"source_package_blanket_exception": {"kind": "locale_aware_source_package", "allowed_file_count": 0, "projection_count": 0, "files": []}},
        },
        "master": {
            "core": master_core(
                release_version=kwargs["release_version"],
                domain_id=domain["code"],
                category_id=category["code"],
                subcategory_id=subcategory["code"],
                document_types=[item["code"] for item in document_types],
                fields=field_codes,
                row_types=[item["code"] for item in row_types],
                cell_codes=cell_codes,
            ),
            "texts": {
                locale: master_text(
                    archive_description=kwargs["archive_description"],
                    domain=domain,
                    category=category,
                    subcategory=subcategory,
                    document_types=document_types,
                    field_codes=field_codes,
                    row_types=row_types,
                    cell_codes=cell_codes,
                )
            },
        },
        "glossaries": {},
        "projections": {
            projection_id: {
                "core": projection_core(
                    projection_id=projection_id,
                    domain_id=domain["code"],
                    document_type_ids=[item["code"] for item in document_types],
                    category_id=category["code"],
                    subcategory_id=subcategory["code"],
                    fields=field_codes,
                    field_ids=[item["code"] for item in field_codes],
                    row_ids=[item["code"] for item in row_types],
                    cell_ids=[item["code"] for item in cell_codes],
                ),
                "texts": {locale: _projection_text(kwargs)},
            }
        },
    }


def _projection_text(values: dict[str, Any]) -> dict[str, Any]:
    payload = values["payload"]
    domain_id = values["domain"]["code"]
    text_markers = values["text_markers"]
    return {
        "label": values["archive_label"],
        "description": values["archive_description"],
        "routing": {
            "when_to_use": required_text(payload.get("when_to_use") or values["archive_description"], label="when_to_use"),
            "avoid_when": required_text(payload.get("avoid_when") or "Do not use for general standard documents without a connection to this special archive.", label="avoid_when"),
        },
        "routing_lexicon": {"text_markers": text_markers, "domain_markers": {domain_id: text_markers[:6]}},
    }


def _term_counts(saved: dict[str, Any]) -> dict[str, int]:
    core = saved["master"]["core"]
    return {
        "domains": len(core["domains"]),
        "document_types": len(core["document_types"]),
        "categories": len(core["categories"]),
        "subcategories": len(core["subcategories"]),
        "field_codes": len(core["field_codes"]),
        "row_types": len(core["row_types"]),
        "cell_codes": len(core["cell_codes"]),
        "projections": len(saved["release"]["projection_ids"]),
    }
