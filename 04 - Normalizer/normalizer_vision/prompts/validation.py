"""Hard output-contract surface for normalizer prompts."""
from __future__ import annotations

from copy import deepcopy

from ..taxonomy import TaxonomyProfile
from .schema_sections import build_default_model_output_schema, build_profile_model_output_schema

MODEL_OUTPUT_SCHEMA = build_default_model_output_schema()


def build_profile_output_schema(profile: TaxonomyProfile) -> dict[str, object]:
    return build_profile_model_output_schema(profile)


def get_output_schema(profile: TaxonomyProfile | None = None) -> dict[str, object]:
    if profile is None:
        return deepcopy(MODEL_OUTPUT_SCHEMA)
    return build_profile_output_schema(profile)


__all__ = ["MODEL_OUTPUT_SCHEMA", "build_profile_output_schema", "get_output_schema"]
