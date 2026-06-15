"""Path helpers for owner action payloads and output dialogs."""
from __future__ import annotations

from pathlib import Path

from .. import validation


def choose_output_path(app, surface_id: str, action_link: dict, *, filedialog) -> Path | None:
    if not action_link.get("requires_output_path"):
        return None
    selected = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON", "*.json"), ("All Files", "*.*")],
        initialdir=str(Path(app._selected_entry().module_root) / "output"),
        initialfile=suggested_output_name(app, surface_id),
    )
    return Path(selected) if selected else None


def suggested_output_name(app, surface_id: str) -> str:
    widget_info = app._action_widgets.get(surface_id) or {}
    surface = widget_info.get("surface")
    value = dict(getattr(surface, "draft", {}) or {})
    release = value.get("release") if isinstance(value.get("release"), dict) else {}
    release_id = str(value.get("release_id") or release.get("release_id") or "semantic_release.default").strip() or "semantic_release.default"
    safe = release_id.replace("/", ".").replace("\\", ".").replace(" ", "_")
    return validation.safe_filename(f"{safe}.json", fallback="semantic_release.default.json")
