"""On-disk regression fixture locations for Corpus Builder tests."""

from __future__ import annotations

from pathlib import Path

REGRESSION_ROOT = Path(__file__).resolve().parent / "regression"
VISION_INVOICE_CASE = REGRESSION_ROOT / "vision_invoice"
FILES_BUDGET_CASE = REGRESSION_ROOT / "files_budget"

__all__ = ["FILES_BUDGET_CASE", "REGRESSION_ROOT", "VISION_INVOICE_CASE"]
