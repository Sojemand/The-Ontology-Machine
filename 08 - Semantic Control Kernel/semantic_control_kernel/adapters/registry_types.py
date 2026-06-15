from __future__ import annotations

from dataclasses import dataclass


KERNEL_INTERNAL_NO_PIPELINE_ADAPTER = "kernel_internal_no_pipeline_adapter"


@dataclass(frozen=True)
class AdapterMapping:
    categories: tuple[str, ...]
    methods: tuple[str, ...]
    capability_status: tuple[str, ...]
    notes: str = ""

    @property
    def dispatchable(self) -> bool:
        return KERNEL_INTERNAL_NO_PIPELINE_ADAPTER not in self.categories


def mapping(
    categories: str | tuple[str, ...],
    methods: str | tuple[str, ...],
    capability_status: str | tuple[str, ...],
    notes: str = "",
) -> AdapterMapping:
    category_tuple = (categories,) if isinstance(categories, str) else categories
    method_tuple = (methods,) if isinstance(methods, str) else methods
    status_tuple = (capability_status,) if isinstance(capability_status, str) else capability_status
    return AdapterMapping(category_tuple, method_tuple, status_tuple, notes)


__all__ = ["AdapterMapping", "KERNEL_INTERNAL_NO_PIPELINE_ADAPTER", "mapping"]
