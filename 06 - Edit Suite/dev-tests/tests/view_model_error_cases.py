from __future__ import annotations

from edit_suite.ui import view_model
from view_model_support import entry


def test_detail_view_surfaces_bundle_errors_in_summary_and_settings() -> None:
    optimizer_entry = entry("01 - Optimizer", "ready")

    detail = view_model.detail_view(optimizer_entry, bundle_error="RuntimeError: boom")
    sections = {section.name: section for section in detail.sections}

    assert "Owner contract could not be loaded" in sections["Summary"].body
    assert "RuntimeError: boom" in sections["Settings"].body
    assert [surface.surface_id for surface in sections["Summary"].surfaces] == ["__bundle_error__"]
    assert [surface.surface_id for surface in sections["Settings"].surfaces] == ["__bundle_error__"]
    assert view_model.preferred_section(detail.sections, "Summary") == "Settings"


def test_detail_view_surfaces_registry_diagnostic_in_readiness_sections() -> None:
    optimizer_entry = entry("01 - Optimizer", "contract_error", diagnostic="RuntimeError: yaml missing")

    detail = view_model.detail_view(optimizer_entry)
    sections = {section.name: section for section in detail.sections}

    assert "RuntimeError: yaml missing" in sections["Summary"].body
    assert "RuntimeError: yaml missing" in sections["Preview/Drift"].body
