"""Modal dialog for creating a new artifact-owned corpus database."""

from __future__ import annotations

import customtkinter as ctk

from . import theme
from . import corpus_db_dialog_support as support


def prompt_new_corpus_db_creation(app, surface_id: str, action_link: dict, payload: dict) -> dict[str, str] | None:
    dialog_config = action_link.get("new_corpus_db_dialog")
    if not isinstance(dialog_config, dict):
        return {}
    corpus_root = support.resolve_corpus_root(app, payload)
    locale_options = support.locale_options(dialog_config)
    default_locale = support.default_locale(app, surface_id, dialog_config, locale_options)
    label_key = str(dialog_config.get("label_persist_key") or "new_corpus_db_label")
    locale_key = str(dialog_config.get("locale_persist_key") or "new_corpus_db_taxonomy_locale")
    module_context = support.get_module_context(app)
    default_label = str(module_context.get(label_key) or "").strip()
    if not support.has_tk(app):
        raise ValueError("New Corpus DB creation requires an interactive UI dialog.")

    dialog = ctk.CTkToplevel(app)
    dialog.title(str(dialog_config.get("title") or "Create New Corpus DB"))
    dialog.geometry("640x360")
    dialog.minsize(640, 360)
    dialog.transient(app)
    dialog.grab_set()
    dialog.grid_columnconfigure(0, weight=1)
    dialog.grid_rowconfigure(0, weight=1)

    frame = ctk.CTkFrame(dialog)
    frame.grid(row=0, column=0, padx=theme.PADDING_LARGE, pady=theme.PADDING_LARGE, sticky="nsew")
    frame.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        frame,
        text="The new Corpus DB is created and activated only after clicking \"Create\".",
        font=theme.font_header(),
        anchor="w",
        justify="left",
    ).grid(row=0, column=0, sticky="we")
    ctk.CTkLabel(
        frame,
        text=f"Target folder: {corpus_root}",
        font=theme.font_small(),
        text_color=theme.COLOR_MUTED,
        anchor="w",
        justify="left",
    ).grid(row=1, column=0, pady=(theme.PADDING_SMALL, theme.PADDING), sticky="we")

    ctk.CTkLabel(frame, text="Label", font=theme.font_small(), anchor="w").grid(row=2, column=0, sticky="w")
    label_entry = ctk.CTkEntry(frame, height=theme.INPUT_HEIGHT)
    if default_label:
        label_entry.insert(0, default_label)
    label_entry.grid(row=3, column=0, pady=(2, theme.PADDING), sticky="we")

    ctk.CTkLabel(frame, text="Taxonomy language", font=theme.font_small(), anchor="w").grid(row=4, column=0, sticky="w")
    if locale_options:
        locale_var = ctk.StringVar(value=default_locale)
        locale_widget = ctk.CTkOptionMenu(frame, values=list(locale_options), variable=locale_var)
        locale_widget.grid(row=5, column=0, pady=(2, theme.PADDING), sticky="we")
    else:
        locale_widget = ctk.CTkEntry(frame, height=theme.INPUT_HEIGHT)
        locale_widget.insert(0, default_locale)
        locale_widget.grid(row=5, column=0, pady=(2, theme.PADDING), sticky="we")

    ctk.CTkLabel(frame, text="File preview", font=theme.font_small(), anchor="w").grid(row=6, column=0, sticky="w")
    preview_var = ctk.StringVar(value="")
    preview_entry = ctk.CTkEntry(frame, height=theme.INPUT_HEIGHT, textvariable=preview_var)
    preview_entry.grid(row=7, column=0, pady=(2, theme.PADDING_SMALL), sticky="we")
    preview_entry.configure(state="readonly")

    error_var = ctk.StringVar(value="")
    ctk.CTkLabel(frame, textvariable=error_var, font=theme.font_small(), text_color=theme.COLOR_ERROR, anchor="w", justify="left").grid(
        row=8, column=0, pady=(0, theme.PADDING_SMALL), sticky="we"
    )

    result: dict[str, str] = {}

    def current_locale() -> str:
        if locale_options:
            return str(locale_var.get()).strip()
        return str(locale_widget.get()).strip()

    def update_preview(*_args) -> None:
        label = support.safe_segment(label_entry.get(), fallback="corpus")
        locale = support.safe_segment(current_locale().lower(), fallback="und")
        preview_var.set(str((corpus_root / support.build_filename(label, locale)).resolve()))
        error_var.set("")

    def submit() -> None:
        label = str(label_entry.get()).strip()
        locale = current_locale().lower()
        if not label:
            error_var.set("Label is required.")
            return
        if not locale:
            error_var.set("Taxonomy language is required.")
            return
        result[str(dialog_config.get("label_name") or "database_label")] = label
        result[str(dialog_config.get("locale_name") or "taxonomy_locale")] = locale
        module_context[label_key] = label
        module_context[locale_key] = locale
        artifact_path = support.write_confirmation_artifact(
            app,
            surface_id,
            action=str(action_link.get("action") or "").strip(),
            database_label=label,
            taxonomy_locale=locale,
        )
        result["confirmation_artifact_path"] = str(artifact_path)
        dialog.destroy()

    def cancel() -> None:
        result.clear()
        dialog.destroy()

    label_entry.bind("<KeyRelease>", update_preview)
    if locale_options:
        locale_widget.configure(command=lambda _choice: update_preview())
    else:
        locale_widget.bind("<KeyRelease>", update_preview)
    buttons = ctk.CTkFrame(frame, fg_color=frame.cget("fg_color"))
    buttons.grid(row=9, column=0, pady=(theme.PADDING_SMALL, 0), sticky="e")
    ctk.CTkButton(buttons, text="Cancel", width=120, command=cancel).grid(row=0, column=0, padx=(0, theme.PADDING_SMALL))
    ctk.CTkButton(buttons, text="Create", width=140, command=submit).grid(row=0, column=1)

    dialog.protocol("WM_DELETE_WINDOW", cancel)
    update_preview()
    label_entry.focus_set()
    app.wait_window(dialog)
    if not result:
        return None
    return {"confirmation_artifact_path": str(result["confirmation_artifact_path"])}
