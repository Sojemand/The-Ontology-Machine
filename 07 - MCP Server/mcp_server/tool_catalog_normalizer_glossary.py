from __future__ import annotations

from typing import Any

from .tool_catalog_utils import _tool


def translation_glossary_tools() -> list[dict[str, Any]]:
    return [
        _tool(
            "read_translation_glossary",
            "Read locale-specific terminology entries for the source-backed translation glossary. This is the atomic read tool; it does not validate, write, translate, compile, export, or activate. For custom archives, pass artifact_folder so the read uses the workspace-local glossary.",
            {
                "locale": {
                    "type": "string",
                    "description": "Locale whose glossary should be read or edited.",
                },
                "artifact_folder": {
                    "type": "string",
                    "description": "Workspace root for custom/special-purpose authoring. Pass this for custom archives so the glossary stays workspace-local.",
                },
            },
            required=("locale",),
        ),
        _tool(
            "upsert_translation_glossary_entry",
            "Add or replace one locale-specific terminology entry in the source-backed translation glossary. This atomic write validates the owner surface and writes only that updated glossary surface; it does not translate, compile, export, or activate. For custom archives, pass artifact_folder so the edit stays workspace-local.",
            {
                "locale": {
                    "type": "string",
                    "description": "Locale whose glossary should be edited.",
                },
                "english_term": {
                    "type": "string",
                    "description": "Canonical source term key that should map to locale wording.",
                },
                "canonical": {
                    "type": "string",
                    "description": "Preferred locale wording for this source term.",
                },
                "aliases": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional extra locale spellings or synonyms.",
                },
                "artifact_folder": {
                    "type": "string",
                    "description": "Workspace root for custom/special-purpose authoring. Pass this for custom archives so the glossary stays workspace-local.",
                },
            },
            required=("locale", "english_term", "canonical"),
        ),
        _tool(
            "remove_translation_glossary_entry",
            "Remove one locale-specific terminology entry from the source-backed translation glossary. This atomic write validates the owner surface and writes only that updated glossary surface; it does not translate, compile, export, or activate. For custom archives, pass artifact_folder so the edit stays workspace-local.",
            {
                "locale": {
                    "type": "string",
                    "description": "Locale whose glossary should be edited.",
                },
                "english_term": {
                    "type": "string",
                    "description": "Canonical source term key to remove.",
                },
                "artifact_folder": {
                    "type": "string",
                    "description": "Workspace root for custom/special-purpose authoring. Pass this for custom archives so the glossary stays workspace-local.",
                },
            },
            required=("locale", "english_term"),
        ),
    ]


__all__ = ["translation_glossary_tools"]
