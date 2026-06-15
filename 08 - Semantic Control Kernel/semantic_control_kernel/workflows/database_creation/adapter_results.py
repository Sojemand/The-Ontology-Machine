from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.types.adapter_results import AdapterCallResult, MissingCapabilityBlocker


def is_missing_capability(value: object) -> bool:
    return isinstance(value, MissingCapabilityBlocker)


def is_adapter_ok(value: object) -> bool:
    return isinstance(value, AdapterCallResult) and value.status == "ok"


def adapter_output(value: object) -> dict[str, Any]:
    if isinstance(value, AdapterCallResult):
        payload = value.to_dict()
        output_refs = payload.get("output_refs")
        if isinstance(output_refs, Mapping):
            return dict(output_refs)
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    return {}
