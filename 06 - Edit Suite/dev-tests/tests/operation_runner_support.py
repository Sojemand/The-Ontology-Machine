from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from edit_suite.registry.types import ModuleReadinessEntry
from edit_suite.surfaces import DraftState
from edit_suite.surfaces.types import SurfaceModel
from edit_suite.ui.corpus_db_dialog import prompt_new_corpus_db_creation
from edit_suite.ui import corpus_db_dialog_support, operation_runner


def _hardlink_or_skip(source: Path, link: Path) -> None:
    try:
        os.link(source, link)
    except OSError as exc:
        pytest.skip(f"hardlink probe unavailable: {exc}")


class _Entry:
    def __init__(self, value: str) -> None:
        self._value = value

    def get(self) -> str:
        return self._value


class _TextBox:
    def __init__(self, value: str) -> None:
        self._value = value

    def get(self, _start: str, _end: str) -> str:
        return self._value


def _entry(
    *,
    slot_name: str = "04 - Normalizer",
    display_name: str = "Normalizer",
    module_root: str = "C:/Normalizer",
    module_key: str = "normalizer",
    edit_contract_path: str = "normalizer_vision/edit_contract",
) -> ModuleReadinessEntry:
    return ModuleReadinessEntry(
        slot_name=slot_name,
        display_name=display_name,
        module_root=module_root,
        module_key=module_key,
        readiness="ready",
        blockers=(),
        manifest_path="manifest",
        manifest_present=True,
        edit_contract_path=edit_contract_path,
        runtime_available=True,
    )


def _app(surface: SurfaceModel):
    entry = _entry()
    events: list[str] = []
    app = SimpleNamespace(
        _state_root=Path("C:/edit-suite-state"),
        _ui_state={"operation_contexts": {}},
        _selected_module=entry.slot_name,
        _drafts={entry.slot_name: {}},
        _action_widgets={surface.surface_id: {"surface": surface}},
        _operation_results={},
        _render_detail_only=False,
        _selected_entry=lambda: entry,
        _render=lambda: events.append("render"),
    )
    return app, entry, events


def _surface(release_id: str = "semantic/release current") -> SurfaceModel:
    return SurfaceModel(
        surface_id="normalizer.taxonomy_release_draft",
        label="Taxonomy / Projection Release",
        kind="taxonomy_release_draft",
        editable=True,
        editor_kind="taxonomy_release_draft",
        descriptor={},
        value={"release": {"release_id": release_id}},
        draft={"release": {"release_id": release_id}},
        operation_links=(),
    )

__all__ = [
    "json",
    "Path",
    "SimpleNamespace",
    "pytest",
    "DraftState",
    "SurfaceModel",
    "corpus_db_dialog_support",
    "operation_runner",
    "prompt_new_corpus_db_creation",
    "_Entry",
    "_TextBox",
    "_app",
    "_entry",
    "_hardlink_or_skip",
    "_surface",
]
