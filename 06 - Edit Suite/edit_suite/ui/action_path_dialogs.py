"""File dialog helpers for generic owner-action inputs."""
from __future__ import annotations

from pathlib import Path

from .. import validation


def choose_path(app, entry, field_type: str, *, spec: dict | None, widgets: dict | None, filedialog) -> None:
    module_root = Path(app._selected_entry().module_root)
    initialdir = str(_default_dialog_dir(module_root, field_type))
    current_value = str(entry.get()).strip()
    seeded_value = current_value or str((spec or {}).get("default") or "").strip()
    initialfile = None
    if seeded_value:
        initialdir, initialfile = dialog_seed(module_root, seeded_value, default_dir=Path(initialdir))
        if field_type == "save_file" and initialfile:
            initialfile = _safe_dialog_filename(initialfile)
    if field_type == "open_folder":
        value = filedialog.askdirectory(initialdir=initialdir)
    elif field_type == "save_file":
        dialog_kwargs = {"initialdir": initialdir}
        if initialfile:
            dialog_kwargs["initialfile"] = initialfile
        dialog_kwargs.update(_save_dialog_options(spec, widgets, seeded_value, initialfile))
        value = filedialog.asksaveasfilename(**dialog_kwargs)
    else:
        dialog_kwargs = {"initialdir": initialdir}
        if initialfile:
            dialog_kwargs["initialfile"] = initialfile
        value = filedialog.askopenfilename(**dialog_kwargs)
    if value:
        entry.delete(0, "end")
        entry.insert(0, value)


def dialog_seed(module_root: Path, raw_value: str, *, default_dir: Path) -> tuple[str, str | None]:
    candidate = Path(raw_value).expanduser()
    resolved = candidate if candidate.is_absolute() else (module_root / candidate)
    if resolved.exists() and resolved.is_dir():
        return str(resolved), None
    initialdir = resolved.parent if str(resolved.parent) not in {"", "."} else default_dir
    initialfile = resolved.name or None
    return str(initialdir), initialfile


def _default_dialog_dir(module_root: Path, field_type: str) -> Path:
    output_dir = module_root / "output"
    if field_type == "save_file" and output_dir.exists():
        return output_dir
    return module_root


def _save_dialog_options(spec: dict | None, widgets: dict | None, seeded_value: str, initialfile: str | None) -> dict:
    extension = preferred_extension(spec, widgets, seeded_value)
    options: dict[str, object] = {}
    if extension:
        options["defaultextension"] = extension
        options["filetypes"] = [_filetype_for_extension(extension), ("All Files", "*.*")]
    else:
        options["filetypes"] = [("All Files", "*.*")]
    if initialfile:
        return options
    suggested = _suggest_filename(spec, extension)
    if suggested:
        options["initialfile"] = suggested
    return options


def preferred_extension(spec: dict | None, widgets: dict | None, seeded_value: str) -> str | None:
    fmt_item = (widgets or {}).get("fmt")
    if isinstance(fmt_item, dict) and fmt_item.get("kind") == "select":
        value = str(fmt_item["variable"].get()).strip().lower()
        if value in {"csv", "json", "jsonl"}:
            return f".{value}"
    for raw in (seeded_value, str((spec or {}).get("default") or "").strip()):
        suffix = Path(raw).suffix.strip().lower()
        if suffix:
            return suffix
    return None


def _filetype_for_extension(extension: str) -> tuple[str, str]:
    mapping = {
        ".csv": ("CSV", "*.csv"),
        ".db": ("DB", "*.db"),
        ".json": ("JSON", "*.json"),
        ".jsonl": ("JSONL", "*.jsonl"),
    }
    return mapping.get(extension.lower(), (f"{extension.upper()} files", f"*{extension}"))


def _suggest_filename(spec: dict | None, extension: str | None) -> str | None:
    name = str((spec or {}).get("name") or "").strip().lower()
    if name == "output_path":
        stem = "export"
    elif name == "release_path":
        stem = "release"
    elif name:
        stem = name.replace(" ", "_")
    else:
        stem = "output"
    filename = f"{stem}{extension}" if extension else stem
    fallback = f"output{extension or ''}"
    return validation.safe_filename(filename, fallback=fallback)


def _safe_dialog_filename(filename: str) -> str:
    suffix = Path(filename).suffix
    return validation.safe_filename(filename, fallback=f"output{suffix}")
