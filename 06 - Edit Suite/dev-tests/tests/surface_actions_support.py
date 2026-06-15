from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from edit_suite.registry.types import ModuleReadinessEntry
from edit_suite.surfaces.types import SurfaceModel
from edit_suite.ui import surface as ui_surface


class EntryWidget:
    def __init__(self, value: str) -> None:
        self._value = value

    def get(self) -> str:
        return self._value


class FormWidget:
    def __init__(self, values: dict[str, str]) -> None:
        self._entries = {name: EntryWidget(value) for name, value in values.items()}


class JsonWidget:
    def __init__(self, text: str) -> None:
        self._text = text
        self.calls = 0

    def get(self, _start: str, _end: str) -> str:
        self.calls += 1
        return self._text


class PromptBundleWidget:
    def __init__(self, values: dict[str, str]) -> None:
        self._bundle_inputs = {name: JsonWidget(value) for name, value in values.items()}


def entry() -> ModuleReadinessEntry:
    return ModuleReadinessEntry(
        slot_name="01 - Optimizer",
        display_name="Optimizer",
        module_root="C:/ImageOptimizer",
        module_key="optimizer",
        readiness="ready",
        blockers=(),
        manifest_path="manifest",
        manifest_present=True,
        edit_contract_path="ingestion_layer_vision/edit_contract",
        runtime_available=True,
    )


def surface(
    surface_id: str,
    *,
    editor_kind: str,
    editable: bool = True,
    value: dict | None = None,
    draft: dict | None = None,
) -> SurfaceModel:
    payload = value or {"parallel_workers": 4}
    return SurfaceModel(
        surface_id=surface_id,
        label="Settings",
        kind="settings",
        editable=editable,
        editor_kind=editor_kind,
        descriptor={"source_path": "config/config.yaml"},
        value=payload,
        draft=draft or payload,
        operation_links=(),
    )


def app(surface: SurfaceModel, editor) -> tuple[ui_surface.EditSuiteApp, ModuleReadinessEntry]:
    module_entry = entry()
    edit_app = object.__new__(ui_surface.EditSuiteApp)
    edit_app._snapshot = SimpleNamespace(entries=(module_entry,))
    edit_app._selected_module = module_entry.slot_name
    edit_app._state_root = Path("C:/edit-suite-state")
    edit_app._drafts = {}
    edit_app._bundles = {}
    edit_app._bundle_errors = {}
    edit_app._action_widgets = {surface.surface_id: {"surface": surface, "editor": editor}}
    edit_app._render = lambda: None
    return edit_app, module_entry
