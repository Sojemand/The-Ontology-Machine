"""Result builders for staged interpreter runs."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import adapter, domain
from .types import ProviderCall


def build_success_result(
    label: str,
    output_path: Path,
    llm_result: dict[str, Any],
    call: ProviderCall,
    *,
    debug_bundle_path: Path | None,
) -> dict[str, Any]:
    needs_review = bool(llm_result.get("processing", {}).get("needs_review"))
    return {
        "status": "ok_review" if needs_review else "ok",
        "file": label,
        "output_path": str(output_path),
        "debug_bundle_path": str(debug_bundle_path) if debug_bundle_path is not None else "",
        "needs_review": needs_review,
        "review_reason": str(llm_result.get("processing", {}).get("review_reason") or ""),
        "error": None,
        "cost_estimate_usd": domain.estimate_cost(call.resolved_model, call.usage),
    }


def build_error_result(
    label: str,
    output_path: Path,
    stage: str,
    exc: Exception,
    *,
    debug_bundle_path: Path | None,
) -> dict[str, Any]:
    result = adapter.build_batch_error_result(Path(label), output_path, f"{stage}: {exc}")
    result["debug_bundle_path"] = str(debug_bundle_path) if debug_bundle_path is not None else ""
    return result
