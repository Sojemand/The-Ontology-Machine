"""Readable prompt-debug helpers."""
from __future__ import annotations

from ..taxonomy import TaxonomyProfile


def describe_profile(profile: TaxonomyProfile) -> str:
    return "\n".join(
        [
            f"Profile: {profile.projection_id}",
            f"Label: {profile.label}",
            f"Master: {profile.master_taxonomy_id} {profile.master_taxonomy_version}",
            f"Domains: {', '.join(profile.domain_ids)}",
            f"Document types: {len(profile.document_types)}",
            f"Categories: {len(profile.categories)}",
            f"Subcategories: {len(profile.subcategories)}",
            f"Field codes: {len(profile.field_codes)}",
            f"Row types: {len(profile.row_types)}",
            f"Cell codes: {len(profile.cell_codes)}",
        ]
    )


__all__ = ["describe_profile"]
