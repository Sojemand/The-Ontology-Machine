from __future__ import annotations

from typing import Any

import customtkinter as ctk
import pytest

from edit_suite.registry.types import ModuleReadinessEntry
from edit_suite.surfaces.types import SurfaceModel


@pytest.fixture()
def tk_root():
    try:
        root = ctk.CTk()
    except Exception as exc:  # pragma: no cover - depends on local GUI runtime
        pytest.skip(f"Tk runtime unavailable: {exc}")
    root.withdraw()
    try:
        yield root
    finally:
        root.destroy()


def buttons(parent) -> list[ctk.CTkButton]:
    found: list[ctk.CTkButton] = []

    def walk(widget) -> None:
        if isinstance(widget, ctk.CTkButton):
            found.append(widget)
        for child in widget.winfo_children():
            walk(child)

    walk(parent)
    return found


def button(parent, text: str, *, index: int = 0) -> ctk.CTkButton:
    matches = [item for item in buttons(parent) if str(item.cget("text")) == text]
    assert len(matches) > index, f"Missing button {text!r}; saw {[item.cget('text') for item in buttons(parent)]}"
    return matches[index]


def invoke(parent, text: str, *, index: int = 0) -> None:
    invoke_button(button(parent, text, index=index))


def invoke_button(item: ctk.CTkButton) -> None:
    assert str(item.cget("state")) != "disabled"
    top = item.winfo_toplevel()
    item.invoke()
    try:
        top.update()
    except Exception:
        pass


def entry(
    *,
    slot_name: str = "04 - Normalizer",
    module_root: str = "C:/Normalizer",
    module_key: str = "normalizer",
) -> ModuleReadinessEntry:
    return ModuleReadinessEntry(
        slot_name=slot_name,
        display_name="Normalizer",
        module_root=module_root,
        module_key=module_key,
        readiness="ready",
        blockers=(),
        manifest_path="manifest",
        manifest_present=True,
        edit_contract_path="normalizer_vision/edit_contract",
        runtime_available=True,
    )


def surface(
    *,
    surface_id: str = "normalizer.settings",
    editor_kind: str = "form",
    editable: bool = True,
    descriptor: dict[str, Any] | None = None,
    value: dict[str, Any] | None = None,
    draft: dict[str, Any] | None = None,
    operation_links: tuple[dict[str, Any], ...] = (),
) -> SurfaceModel:
    payload = draft or value or {"parallel_workers": 4, "enabled": True}
    return SurfaceModel(
        surface_id=surface_id,
        label="Settings",
        kind="settings",
        editable=editable,
        editor_kind=editor_kind,
        descriptor=descriptor or {},
        value=value or payload,
        draft=payload,
        operation_links=operation_links,
    )


def walk(parent):
    yield parent
    for child in parent.winfo_children():
        yield from walk(child)
