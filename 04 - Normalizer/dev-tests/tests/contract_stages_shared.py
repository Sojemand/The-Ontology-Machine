from __future__ import annotations

from pathlib import Path

import pytest

from normalizer_vision.models import NormalizationResult, NormalizerRuntimeSettings

from normalizer_vision.orchestrator_contract import adapter, validation, workflow

from normalizer_vision.semantic_release import build_semantic_release

PROJECT_ROOT = Path(__file__).resolve().parents[2]

EXPECTED_DEFAULT_PROJECTION_IDS = [
    "business.customer.communication.default.v1",
    "community.spiritual.default.v1",
    "finance.default.v1",
    "health.care.default.v1",
    "housing.default.v1",
    "legal.public_admin.default.v1",
    "operations.default.v1",
    "people.identity.default.v1",
    "personal.expression.default.v1",
    "personal.wellbeing.default.v1",
    "technical.default.v1",
]

__all__ = [name for name in globals() if not name.startswith("__")]
