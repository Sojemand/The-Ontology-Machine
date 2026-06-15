from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.adapters.capabilities import (
    ADAPTER_CATEGORIES,
    FALSE_FRIEND_TOOL_NAMES,
    INVALID_KERNEL_NAME_CANDIDATES,
    PIPELINE_ADAPTER_EXCLUDED_FUNCTIONS,
    REQUIRED_PIPELINE_CAPABILITIES,
)
from semantic_control_kernel.adapters.errors import AdapterDispatchError
from semantic_control_kernel.adapters.registry_classes import ADAPTER_CLASS_MAP
from semantic_control_kernel.adapters.registry_mappings import CANONICAL_FUNCTION_ADAPTER_MAP
from semantic_control_kernel.adapters.registry_types import AdapterMapping, KERNEL_INTERNAL_NO_PIPELINE_ADAPTER
from semantic_control_kernel.types.adapter_results import AdapterCallResult, MissingCapabilityBlocker


class AdapterRegistry:
    def __init__(self, *, state_root: str, pipeline_root: str | None = None) -> None:
        self.state_root = state_root
        self.pipeline_root = pipeline_root

    @classmethod
    def adapter_class_names(cls) -> tuple[str, ...]:
        return tuple(ADAPTER_CLASS_MAP)

    @classmethod
    def canonical_function_names(cls) -> tuple[str, ...]:
        return tuple(CANONICAL_FUNCTION_ADAPTER_MAP)

    @classmethod
    def exported_names(cls) -> tuple[str, ...]:
        return tuple(ADAPTER_CLASS_MAP) + tuple(CANONICAL_FUNCTION_ADAPTER_MAP)

    @classmethod
    def get_mapping(cls, kernel_function: str) -> AdapterMapping:
        try:
            return CANONICAL_FUNCTION_ADAPTER_MAP[kernel_function]
        except KeyError as exc:
            raise AdapterDispatchError(f"Unknown canonical Kernel function: {kernel_function}") from exc

    @classmethod
    def is_pipeline_adapter_dispatchable(cls, kernel_function: str) -> bool:
        if kernel_function in PIPELINE_ADAPTER_EXCLUDED_FUNCTIONS:
            return False
        mapping = CANONICAL_FUNCTION_ADAPTER_MAP.get(kernel_function)
        return bool(mapping and mapping.dispatchable)

    @classmethod
    def can_satisfy_kernel_state_resolver(cls, tool_name: str) -> bool:
        return tool_name not in FALSE_FRIEND_TOOL_NAMES

    def dispatch(self, kernel_function: str, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult | MissingCapabilityBlocker:
        if kernel_function in PIPELINE_ADAPTER_EXCLUDED_FUNCTIONS:
            raise AdapterDispatchError(f"{kernel_function} is not a Pipeline adapter call.")
        mapping = self.get_mapping(kernel_function)
        if not mapping.dispatchable:
            raise AdapterDispatchError(f"{kernel_function} is Kernel-internal and has no Pipeline adapter.")
        first_category = mapping.categories[0]
        adapter_cls = ADAPTER_CLASS_MAP[first_category]
        adapter = adapter_cls(state_root=self.state_root, pipeline_root=self.pipeline_root)
        method_name = mapping.methods[0].split(".")[-1].split(" plus ")[0].split()[0]
        if not hasattr(adapter, method_name):
            raise AdapterDispatchError(f"{first_category}.{method_name} is not implemented.")
        method = getattr(adapter, method_name)
        return method(request_payload or {})


__all__ = (
    "ADAPTER_CATEGORIES",
    "ADAPTER_CLASS_MAP",
    "AdapterMapping",
    "AdapterRegistry",
    "CANONICAL_FUNCTION_ADAPTER_MAP",
    "FALSE_FRIEND_TOOL_NAMES",
    "INVALID_KERNEL_NAME_CANDIDATES",
    "KERNEL_INTERNAL_NO_PIPELINE_ADAPTER",
    "PIPELINE_ADAPTER_EXCLUDED_FUNCTIONS",
    "REQUIRED_PIPELINE_CAPABILITIES",
)
