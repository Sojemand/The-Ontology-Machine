"""Database creation dialog."""

from __future__ import annotations

import customtkinter as ctk

from . import theme
from .dialogs_basic import show_error


def prompt_create_database(
    app,
    *,
    storage_folder: str,
    initial_name: str,
    initial_bootstrap_mode: str,
    initial_taxonomy_locale: str,
    blueprints: list[dict[str, object]],
    blueprint_error: str = "",
) -> dict[str, str] | None:
    window = ctk.CTkToplevel(app)
    window.title("Create Database")
    window.geometry("620x430")
    window.minsize(560, 380)
    if hasattr(window, "transient"):
        window.transient(app)
    if hasattr(window, "grab_set"):
        window.grab_set()

    result: dict[str, str] | None = None
    name_var = ctk.StringVar(value=initial_name)
    blueprint_item = _canonical_create_database_blueprint(blueprints)
    locale_state = _database_locale_state(blueprint_item, initial_taxonomy_locale)
    mode_values = ["Default Release", "No Release"] if locale_state["can_use_blueprint"] else ["No Release"]
    mode_var = ctk.StringVar(value="No Release" if initial_bootstrap_mode == "no_release" or not locale_state["can_use_blueprint"] else "Default Release")
    locale_var = ctk.StringVar(value=locale_state["initial_label"])

    root = _build_database_dialog_header(window, storage_folder, blueprint_error)
    form = ctk.CTkFrame(root, fg_color="transparent")
    form.pack(fill="x")
    ctk.CTkLabel(form, text="Database name", font=theme.font_normal()).pack(anchor="w")
    name_entry = ctk.CTkEntry(form, textvariable=name_var, height=theme.INPUT_HEIGHT)
    name_entry.pack(fill="x", pady=(4, theme.PADDING_SMALL))
    mode_selector, mode_hint = _build_mode_selector(form, mode_var, mode_values)
    locale_selector, locale_description = _build_locale_selector(form, locale_var, locale_state)

    def _refresh_locale_info() -> None:
        selected_locale = locale_state["locale_by_label"].get(str(locale_var.get() or "").strip(), "")
        locale_description.configure(text=f"The runtime language pack for the new DB will be set to {_format_locale_label(selected_locale)}." if selected_locale else "No language selected.")

    def _refresh_mode_state() -> None:
        use_blueprint = mode_var.get() == "Default Release" and locale_state["can_use_blueprint"]
        locale_selector.configure(state="normal" if use_blueprint else "disabled")
        mode_hint.configure(
            text="The new DB will be initialized directly with a Semantic Release exported from the canonical default taxonomy package."
            if use_blueprint
            else "Only an empty DB file will be created. A release must be activated before the first run."
        )

    _refresh_locale_info()
    _refresh_mode_state()
    if locale_state["can_use_blueprint"]:
        locale_selector.configure(command=lambda _value: _refresh_locale_info())
    mode_selector.configure(command=lambda _value: _refresh_mode_state())

    actions = ctk.CTkFrame(root, fg_color="transparent")
    actions.pack(fill="x", pady=(theme.PADDING, 0))

    def _submit() -> None:
        nonlocal result
        name = name_var.get().strip()
        if not name:
            show_error("Database name must not be empty.")
            return
        selected_locale = _selected_database_locale(mode_var.get(), locale_var.get(), locale_state)
        if selected_locale is None:
            return
        result = {
            "database_name": name,
            "bootstrap_mode": "no_release" if mode_var.get() == "No Release" else "default_release",
            "taxonomy_locale": selected_locale,
        }
        window.destroy()

    ctk.CTkButton(actions, text="Cancel", width=110, height=theme.BUTTON_HEIGHT, command=window.destroy).pack(side="right")
    ctk.CTkButton(actions, text="Create Database", width=140, height=theme.BUTTON_HEIGHT, command=_submit).pack(side="right", padx=(0, 8))
    _focus_dialog(window, name_entry)
    window.wait_window()
    return result


def _database_locale_state(blueprint_item: dict[str, object] | None, initial_taxonomy_locale: str) -> dict[str, object]:
    available_locales = list(blueprint_item.get("available_locales") or []) if blueprint_item else []
    default_runtime_locale = str(blueprint_item.get("default_runtime_locale") or "").strip().lower() if blueprint_item else ""
    default_taxonomy_locale = (
        initial_taxonomy_locale.strip().lower()
        if initial_taxonomy_locale.strip().lower() in available_locales
        else default_runtime_locale if default_runtime_locale in available_locales
        else (available_locales[0] if available_locales else "")
    )
    locale_labels = [_format_locale_label(locale) for locale in available_locales]
    locale_by_label = {label: locale for label, locale in zip(locale_labels, available_locales, strict=False)}
    label_by_locale = {locale: label for label, locale in locale_by_label.items()}
    return {
        "available_locales": available_locales,
        "can_use_blueprint": bool(blueprint_item and available_locales),
        "initial_label": label_by_locale.get(default_taxonomy_locale, locale_labels[0] if locale_labels else "-"),
        "locale_by_label": locale_by_label,
        "locale_labels": locale_labels,
    }


def _build_database_dialog_header(window, storage_folder: str, blueprint_error: str):
    root = ctk.CTkFrame(window)
    root.pack(fill="both", expand=True, padx=theme.PADDING, pady=theme.PADDING)
    ctk.CTkLabel(root, text="Create Database", font=theme.font_header(), text_color=theme.COLOR_TEXT, anchor="w").pack(fill="x")
    ctk.CTkLabel(
        root,
        text="Create a new target database in the selected storage folder and choose whether it is initialized immediately with the canonical default taxonomy package.",
        font=theme.font_small(),
        text_color=theme.COLOR_MUTED,
        justify="left",
        wraplength=560,
    ).pack(fill="x", pady=(4, theme.PADDING_SMALL))
    ctk.CTkLabel(root, text=f"Storage Folder: {storage_folder}", font=theme.font_small(), text_color=theme.COLOR_MUTED, justify="left", wraplength=560).pack(fill="x", pady=(0, theme.PADDING_SMALL))
    if blueprint_error:
        ctk.CTkLabel(
            root,
            text=f"Default taxonomy could not be loaded: {blueprint_error}",
            font=theme.font_small(),
            text_color=theme.COLOR_WARNING,
            justify="left",
            wraplength=560,
        ).pack(fill="x", pady=(0, theme.PADDING_SMALL))
    return root


def _build_mode_selector(form, mode_var, mode_values):
    ctk.CTkLabel(form, text="Initial semantic setup", font=theme.font_normal()).pack(anchor="w")
    mode_selector = ctk.CTkSegmentedButton(form, values=mode_values, variable=mode_var)
    mode_selector.pack(fill="x", pady=(4, theme.PADDING_SMALL))
    mode_hint = ctk.CTkLabel(form, text="", font=theme.font_small(), text_color=theme.COLOR_MUTED, justify="left", wraplength=560)
    mode_hint.pack(fill="x")
    return mode_selector, mode_hint


def _build_locale_selector(form, locale_var, locale_state: dict[str, object]):
    locale_frame = ctk.CTkFrame(form, fg_color="transparent")
    locale_frame.pack(fill="x", pady=(theme.PADDING_SMALL, 0))
    ctk.CTkLabel(locale_frame, text="Language", font=theme.font_normal()).pack(anchor="w")
    locale_selector = ctk.CTkOptionMenu(
        locale_frame,
        values=locale_state["locale_labels"] or ["-"],
        variable=locale_var,
        state="normal" if locale_state["can_use_blueprint"] else "disabled",
    )
    locale_selector.pack(fill="x", pady=(4, 6))
    locale_description = ctk.CTkLabel(locale_frame, text="", font=theme.font_small(), text_color=theme.COLOR_MUTED, justify="left", wraplength=560)
    locale_description.pack(fill="x")
    return locale_selector, locale_description


def _selected_database_locale(mode: str, locale_label: str, locale_state: dict[str, object]) -> str | None:
    if mode != "Default Release":
        return ""
    selected_locale = locale_state["locale_by_label"].get(str(locale_label or "").strip(), "")
    if not selected_locale:
        show_error("Select a language for the new database.")
        return None
    return selected_locale


def _focus_dialog(window, entry) -> None:
    if hasattr(window, "lift"):
        window.lift()
    if hasattr(window, "focus_force"):
        window.focus_force()
    if hasattr(entry, "focus_set"):
        entry.focus_set()


def _canonical_create_database_blueprint(blueprints: list[dict[str, object]]) -> dict[str, object] | None:
    for item in blueprints:
        if str(item.get("blueprint_ref") or "").strip() == "default":
            return item
    return None


def _format_locale_label(locale: str) -> str:
    normalized = str(locale or "").strip().lower()
    return normalized or "-"
