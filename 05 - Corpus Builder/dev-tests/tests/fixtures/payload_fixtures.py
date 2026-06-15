"""Fixture payloads loaded from on-disk regression cases."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from .regression_cases import FILES_BUDGET_CASE, VISION_INVOICE_CASE


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture()
def vision_structured() -> dict:
    return _load_json(VISION_INVOICE_CASE / "invoice.structured.json")


@pytest.fixture()
def vision_normalized() -> dict:
    return _load_json(VISION_INVOICE_CASE / "invoice.structured.normalized.json")


@pytest.fixture()
def vision_validation_report() -> dict:
    return _load_json(VISION_INVOICE_CASE / "invoice.vision_validation_report.json")


@pytest.fixture()
def mixed_structured() -> dict:
    return _load_json(FILES_BUDGET_CASE / "budget.structured.json")


@pytest.fixture()
def files_validation_report() -> dict:
    return _load_json(FILES_BUDGET_CASE / "budget.files_validation_report.json")


@pytest.fixture()
def legacy_validation_report() -> dict:
    return _load_json(FILES_BUDGET_CASE / "budget.validation_report.json")
