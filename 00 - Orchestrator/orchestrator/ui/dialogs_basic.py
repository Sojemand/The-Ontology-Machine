"""Basic messagebox and filepicker dialogs for the Orchestrator UI."""

from __future__ import annotations

from tkinter import filedialog, messagebox


def show_error(message: str) -> None:
    messagebox.showerror("Orchestrator", message)


def confirm_reset(app) -> bool:
    return bool(
        messagebox.askyesno(
            "Orchestrator",
            "Really reset the Error Bundle?\n\n"
            "This only removes the 'Error Cases' tree. "
            "Original files stored there are moved back into the input directory when possible. "
            "Successful artifacts, corpus.db, and successful run history are preserved.",
            icon="warning",
        )
    )


def confirm_reset_pipeline_logs(app) -> bool:
    return bool(
        messagebox.askyesno(
            "Orchestrator",
            "Really delete hidden pipeline logs?\n\n"
            "This removes state/pipeline/... including pipeline_state.json and runs/, as well as "
            "state/orchestrator.log and backups. Artifacts, corpus.db, debug output, "
            "credentials, and settings are preserved.",
            icon="warning",
        )
    )


def confirm_reset_debug_output(app) -> bool:
    return bool(
        messagebox.askyesno(
            "Orchestrator",
            "Really delete debug output?\n\n"
            "This only removes state/debug_sessions/... including outputs/, request.json, "
            "response.json, snapshot.json, result.json, run.log, home/, and cancel.request. "
            "Replay imports, debug_host_state.json, and the normal pipeline reset are left untouched.",
            icon="warning",
        )
    )


def select_input_folder(app) -> str:
    return filedialog.askdirectory(parent=app, title="Select Input Folder")


def select_artifact_folder(app) -> str:
    return filedialog.askdirectory(parent=app, title="Select Artifact Folder")


def select_release_file(app) -> str:
    return filedialog.askopenfilename(parent=app, title="Select Semantic Release", filetypes=(("JSON", "*.json"), ("All files", "*.*")))


def select_corpus_folder(app) -> str:
    return filedialog.askdirectory(parent=app, title="Select Database Storage Folder")


def select_database_file(app, *, initial_dir: str | None = None) -> str:
    return filedialog.askopenfilename(
        parent=app,
        title="Select Database",
        initialdir=initial_dir or None,
        filetypes=(("SQLite", "*.db *.sqlite *.sqlite3"), ("All files", "*.*")),
    )


def select_debug_artifact_file(app) -> str:
    return filedialog.askopenfilename(
        parent=app,
        title="Select Debug Artifact",
        filetypes=(("JSON/Text", "*.json *.txt *.log *.md"), ("All files", "*.*")),
    )


def select_debug_artifact_dir(app) -> str:
    return filedialog.askdirectory(parent=app, title="Select Debug Artifact Folder")


def select_debug_input_path(
    app,
    *,
    select_file: bool,
    title: str = "",
    filetypes: tuple[tuple[str, str], ...] | None = None,
) -> str:
    if select_file:
        return filedialog.askopenfilename(
            parent=app,
            title=title or "Select Debug Input File",
            filetypes=filetypes or (("All files", "*.*"),),
        )
    return filedialog.askdirectory(parent=app, title=title or "Select Debug Input Folder")


def select_debug_source_path(app) -> str:
    return filedialog.askopenfilename(parent=app, title="Select Debug Source File", filetypes=(("All files", "*.*"),))


def confirm_release_activation(app, *, title: str, body: str) -> bool:
    return bool(messagebox.askyesno("Orchestrator", f"{title}\n\n{body}", parent=app, icon="warning"))
