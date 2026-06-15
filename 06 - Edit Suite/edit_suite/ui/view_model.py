"""View-model helpers for module-first Edit Suite rendering."""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..registry.types import ModuleReadinessEntry, RegistrySnapshot
from ..surfaces import DraftState, ModuleSurfaceBundle, build_sections
from ..surfaces.types import SectionModel

_SLOT_PREFIX_RE = re.compile(r"^\d{2}[a-z]?\s-\s")
_SIDEBAR_TITLE_OVERRIDES = {
    "orchestrator": "Orchestrator",
    "optimizer": "Optimizer",
    "tables optimizer": "Table Optimizer",
    "table optimizer": "Table Optimizer",
    "interpreter": "Interpreter",
    "interpreter tables": "Tables Interpreter",
    "validator": "Validator",
    "normalizer": "Normalizer",
    "corpus builder": "Corpus Builder",
}
_SIDEBAR_BLOCKER_LABELS = {
    "placeholder_module": "Placeholder: no contract yet",
    "missing_edit_contract": "Notice: no contract yet",
    "contract_error": "Notice: contract error",
    "missing_manifest": "Notice: manifest missing",
    "manifest_error": "Notice: manifest error",
    "runtime_unavailable": "Notice: runtime missing",
}


@dataclass(frozen=True)
class ModuleListItem:
    key: str
    title: str
    subtitle: str
    badge: str


@dataclass(frozen=True)
class DetailView:
    title: str
    subtitle: str
    status: str
    sections: tuple[SectionModel, ...]


def list_items(snapshot: RegistrySnapshot) -> tuple[ModuleListItem, ...]:
    items = []
    for entry in snapshot.entries:
        items.append(
            ModuleListItem(
                key=entry.slot_name,
                title=_sidebar_title(entry),
                subtitle=_sidebar_subtitle(entry),
                badge=entry.readiness,
            )
        )
    return tuple(items)


def detail_view(
    entry: ModuleReadinessEntry,
    *,
    bundle: ModuleSurfaceBundle | None = None,
    drafts: dict[str, DraftState] | None = None,
    bundle_error: str = "",
    loading_message: str = "",
    status_text: str = "",
    operation_results: dict[str, dict] | None = None,
) -> DetailView:
    sections = build_sections(
        entry,
        bundle,
        drafts or {},
        bundle_error=bundle_error,
        loading_message=loading_message,
        operation_results=operation_results,
    )
    subtitle = entry.module_key or entry.slot_name
    return DetailView(title=entry.display_name, subtitle=subtitle, status=status_text or entry.readiness, sections=sections)


def preferred_module_key(snapshot: RegistrySnapshot, selected_key: str) -> str:
    entries = list(snapshot.entries)
    selected_entry = next((entry for entry in entries if entry.slot_name == selected_key), None)
    if selected_entry is not None and selected_entry.readiness == "ready":
        return selected_entry.slot_name
    first_ready = next((entry.slot_name for entry in entries if entry.readiness == "ready"), "")
    if first_ready:
        return first_ready
    if selected_entry is not None:
        return selected_entry.slot_name
    return entries[0].slot_name if entries else ""


def preferred_section(sections: tuple[SectionModel, ...], current_section: str) -> str:
    section_names = {section.name for section in sections}
    if current_section in section_names and current_section != "Summary":
        return current_section
    for candidate in ("Settings", "Prompts/Assets", "Operations", "Preview/Drift"):
        if any(section.name == candidate and section.surfaces for section in sections):
            return candidate
    return "Summary" if "Summary" in section_names else next(iter(section_names), "Summary")


def _sidebar_title(entry: ModuleReadinessEntry) -> str:
    base_name = _SLOT_PREFIX_RE.sub("", entry.slot_name).strip() or entry.display_name.strip() or entry.slot_name
    return _SIDEBAR_TITLE_OVERRIDES.get(base_name.casefold(), base_name)


def _sidebar_subtitle(entry: ModuleReadinessEntry) -> str:
    if not entry.blockers:
        return ""
    labels = [_SIDEBAR_BLOCKER_LABELS.get(blocker, blocker.replace("_", " ")) for blocker in entry.blockers]
    return " | ".join(labels)
