from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

def _taxonomy_core_from_proposal(taxonomy_proposal: Mapping[str, Any]) -> dict[str, Any]:
    core = deepcopy(dict(taxonomy_proposal.get("taxonomy_core", taxonomy_proposal)))
    core.pop("taxonomy_id", None)
    for _path, container in _iter_status_containers(core):
        if container.get("status") == "draft":
            container["status"] = "active"
    return core


def _taxonomy_text_from_proposal(taxonomy_proposal: Mapping[str, Any], runtime_locale: str) -> dict[str, Any]:
    text = deepcopy(dict(taxonomy_proposal.get("taxonomy_text", {})))
    text.setdefault("locale", runtime_locale)
    text.setdefault("terms", {})
    return text


def _semantic_binding_from_proposal(taxonomy_proposal: Mapping[str, Any]) -> dict[str, Any]:
    return deepcopy(
        dict(
            taxonomy_proposal.get(
                "semantic_binding",
                {
                    "field_codes": [],
                    "row_types": [],
                    "cell_codes": [],
                },
            )
        )
    )

def _iter_status_containers(value: Any, path: str = "$"):
    if isinstance(value, Mapping):
        if "status" in value:
            yield path, value
        for key, child in value.items():
            yield from _iter_status_containers(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_status_containers(child, f"{path}[{index}]")
