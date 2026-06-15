"""Section building for owner-provided and readiness-only surfaces."""
from __future__ import annotations

import difflib
import json
from typing import Any

from .. import policy
from ..registry.types import ModuleReadinessEntry
from .operation_models import operation_preview_models
from .section_assignment import grouped_surface_models, preview_models
from .summary_builder import summary_body
from .types import DraftState, ModuleSurfaceBundle, SectionModel, SurfaceModel


def build_sections(
    entry: ModuleReadinessEntry,
    bundle: ModuleSurfaceBundle | None,
    drafts: dict[str, DraftState],
    *,
    bundle_error: str = "",
    loading_message: str = "",
    operation_results: dict[str, dict] | None = None,
) -> tuple[SectionModel, ...]:
    if bundle_error and bundle is None:
        return _bundle_error_sections(entry, bundle_error)
    if loading_message and bundle is None:
        return _loading_sections(entry, loading_message)
    if bundle is None:
        return _readiness_sections(entry)
    grouped = grouped_surface_models(bundle, drafts)
    grouped["Preview/Drift"] = (
        grouped.get("Preview/Drift", ())
        + preview_models(bundle, drafts, diff_text=diff_text)
        + operation_preview_models(operation_results or {})
    )
    sections = [
        SectionModel(
            "Summary",
            "Summary",
            f"{entry.display_name} - Summary",
            summary_body(entry, bundle),
            summary_cards=bundle.summary_cards,
        )
    ]
    for name, label in policy.SECTION_ORDER[1:]:
        body = "Owner-provided surface data loaded." if grouped.get(name) else "No owner-provided surface in this section."
        sections.append(SectionModel(name, label, f"{entry.display_name} - {label}", body, surfaces=grouped.get(name, ())))
    return tuple(sections)


def diff_text(current: dict[str, Any], draft: dict[str, Any]) -> str:
    before = json.dumps(current, indent=2, ensure_ascii=False).splitlines()
    after = json.dumps(draft, indent=2, ensure_ascii=False).splitlines()
    lines = difflib.unified_diff(before, after, fromfile="current", tofile="draft", lineterm="")
    return "\n".join(lines) or "No drift."


def _readiness_sections(entry: ModuleReadinessEntry) -> tuple[SectionModel, ...]:
    diagnostic = f"\nDiagnostic: {entry.diagnostic}" if entry.diagnostic else ""
    bodies = {
        "Summary": summary_body(entry, ModuleSurfaceBundle(source="readiness", surfaces=(), module_summary="")),
        "Settings": "No owner-provided settings surface yet. Without edit_contract, this section remains read-only.",
        "Prompts/Assets": "No owner-provided prompt_bundle or asset surface available yet.",
        "Operations": "No generic operation_links visible yet. Non-config actions remain owner-provided.",
        "Preview/Drift": f"Blockers: {', '.join(entry.blockers) or 'none'}{diagnostic}",
    }
    return tuple(SectionModel(name, label, f"{entry.display_name} - {label}", bodies[name]) for name, label in policy.SECTION_ORDER)


def _bundle_error_sections(entry: ModuleReadinessEntry, bundle_error: str) -> tuple[SectionModel, ...]:
    error_value = {"module": entry.slot_name, "display_name": entry.display_name, "readiness": entry.readiness, "edit_contract_path": entry.edit_contract_path, "error": bundle_error}
    error_surface = SurfaceModel(
        surface_id="__bundle_error__",
        label="Bundle Error",
        kind="contract_error",
        editable=False,
        editor_kind="readonly",
        descriptor={"source_path": entry.edit_contract_path or entry.module_root, "editable": False, "preview": ["summary", "json"]},
        value=error_value,
        draft=error_value,
        operation_links=(),
        message="Error loading owner contract",
        load_error=bundle_error,
    )
    bodies = {
        "Summary": f"Owner contract could not be loaded.\nError: {bundle_error}",
        "Settings": f"Configuration surfaces could not be loaded.\nError: {bundle_error}",
        "Prompts/Assets": f"Ruleset/asset surfaces could not be loaded.\nError: {bundle_error}",
        "Operations": f"Operation links could not be loaded.\nError: {bundle_error}",
        "Preview/Drift": f"Preview could not be loaded.\nError: {bundle_error}",
    }
    return (
        SectionModel("Summary", "Summary", f"{entry.display_name} - Summary", bodies["Summary"], surfaces=(error_surface,)),
        SectionModel("Settings", "Settings", f"{entry.display_name} - Settings", bodies["Settings"], surfaces=(error_surface,)),
        SectionModel("Prompts/Assets", "Prompts/Assets", f"{entry.display_name} - Prompts/Assets", bodies["Prompts/Assets"]),
        SectionModel("Operations", "Operations", f"{entry.display_name} - Operations", bodies["Operations"]),
        SectionModel("Preview/Drift", "Preview/Drift", f"{entry.display_name} - Preview/Drift", bodies["Preview/Drift"], surfaces=(error_surface,)),
    )


def _loading_sections(entry: ModuleReadinessEntry, loading_message: str) -> tuple[SectionModel, ...]:
    payload = {"module": entry.slot_name, "status": "loading", "message": loading_message}
    loading_surface = SurfaceModel(
        surface_id="__bundle_loading__",
        label="Loading",
        kind="loading",
        editable=False,
        editor_kind="readonly",
        descriptor={"source_path": entry.edit_contract_path or entry.module_root, "editable": False},
        value=payload,
        draft=payload,
        operation_links=(),
        message=loading_message,
    )
    text = f"Owner contract is loading in the background.\nStatus: {loading_message}"
    return tuple(
        SectionModel(name, label, f"{entry.display_name} - {label}", text, surfaces=(loading_surface,))
        for name, label in policy.SECTION_ORDER
    )
