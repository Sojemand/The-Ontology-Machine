from __future__ import annotations

from typing import Any

from .product_semantics import explain_capabilities, inspect_product_context, recommend_next_steps


def inspect_pipeline_product_context(arguments: dict[str, Any]) -> dict[str, Any]:
    return inspect_product_context(arguments)


def explain_pipeline_capabilities(arguments: dict[str, Any]) -> dict[str, Any]:
    return explain_capabilities(arguments)


def recommend_pipeline_next_steps(arguments: dict[str, Any]) -> dict[str, Any]:
    return recommend_next_steps(arguments)


__all__ = [name for name in globals() if not name.startswith("__")]
