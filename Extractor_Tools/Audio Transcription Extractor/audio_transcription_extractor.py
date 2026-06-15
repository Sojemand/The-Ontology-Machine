from __future__ import annotations

# cspell:words combobox padx pady textvariable yscrollcommand

import argparse
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from audio_transcription_core import collect_media_files, main_cli, transcribe_many
from audio_types import AUTH_MODES, MODEL_CHOICES, TIMESTAMP_MODEL, TranscriptionOptions


AUTH_LABEL_TO_MODE = {
    "Auto (recommended)": "auto",
    "API key only": "api_key",
    "Frontend OAuth test": "frontend_oauth",
}
AUTH_MODE_TO_LABEL = {value: key for key, value in AUTH_LABEL_TO_MODE.items()}


class AudioTranscriptionApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Audio Transcription Extractor")
        self.geometry("920x720")
        self.minsize(780, 600)
        self._messages: queue.Queue[tuple[str, object]] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._stop_requested = threading.Event()
        self.output_dir = tk.StringVar(value="")
        self.model = tk.StringVar(value=TIMESTAMP_MODEL)
        self.language = tk.StringVar(value="de")
        self.auth_label = tk.StringVar(value=AUTH_MODE_TO_LABEL["auto"])
        self.api_key = tk.StringVar(value="")
        self.save_raw_json = tk.BooleanVar(value=True)
        self.overwrite = tk.BooleanVar(value=False)
        self.timeout_seconds = tk.IntVar(value=600)
        self.sleep_seconds = tk.DoubleVar(value=0.0)
        self._build_ui()
        self.after(100, self._poll_messages)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)
        root.rowconfigure(5, weight=1)

        ttk.Label(root, text="Choose audio/video files or folders, then create Markdown transcripts.", font=("", 11, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 8))

        input_frame = ttk.LabelFrame(root, text="Input files and folders")
        input_frame.grid(row=1, column=0, sticky="nsew")
        input_frame.rowconfigure(0, weight=1)
        input_frame.columnconfigure(0, weight=1)
        self.input_text = tk.Text(input_frame, height=10, wrap=tk.NONE, undo=True)
        self.input_text.grid(row=0, column=0, sticky="nsew")
        self._attach_text_context_menu(self.input_text, readonly=False)
        input_scroll = ttk.Scrollbar(input_frame, orient=tk.VERTICAL, command=self.input_text.yview)
        input_scroll.grid(row=0, column=1, sticky="ns")
        self.input_text.configure(yscrollcommand=input_scroll.set)
        buttons = ttk.Frame(input_frame)
        buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(buttons, text="Choose files...", command=self._choose_files).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(buttons, text="Choose folder...", command=self._choose_folder).pack(side=tk.LEFT)

        output = ttk.Frame(root)
        output.grid(row=2, column=0, sticky="ew", pady=10)
        output.columnconfigure(1, weight=1)
        ttk.Label(output, text="Output folder").grid(row=0, column=0, sticky="w", padx=(0, 8))
        output_entry = ttk.Entry(output, textvariable=self.output_dir)
        output_entry.grid(row=0, column=1, sticky="ew")
        self._attach_entry_context_menu(output_entry)
        ttk.Button(output, text="Choose...", command=self._choose_output_dir).grid(row=0, column=2, padx=(8, 0))

        model_row = ttk.Frame(root)
        model_row.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(model_row, text="Model").pack(side=tk.LEFT)
        ttk.Combobox(model_row, textvariable=self.model, values=MODEL_CHOICES, state="readonly", width=24).pack(side=tk.LEFT, padx=(4, 16))
        ttk.Label(model_row, text="Language").pack(side=tk.LEFT)
        language_entry = ttk.Entry(model_row, textvariable=self.language, width=7)
        language_entry.pack(side=tk.LEFT, padx=(4, 16))
        self._attach_entry_context_menu(language_entry)
        ttk.Label(model_row, text="Auth").pack(side=tk.LEFT)
        ttk.Combobox(model_row, textvariable=self.auth_label, values=list(AUTH_LABEL_TO_MODE.keys()), state="readonly", width=22).pack(side=tk.LEFT, padx=(4, 16))
        ttk.Label(model_row, text="Timeout").pack(side=tk.LEFT)
        ttk.Spinbox(model_row, from_=30, to=7200, increment=30, textvariable=self.timeout_seconds, width=6).pack(side=tk.LEFT, padx=(4, 0))

        key_row = ttk.Frame(root)
        key_row.grid(row=4, column=0, sticky="ew", pady=(0, 8))
        key_row.columnconfigure(1, weight=1)
        ttk.Label(key_row, text="API key override").grid(row=0, column=0, sticky="w", padx=(0, 8))
        key_entry = ttk.Entry(key_row, textvariable=self.api_key, show="*")
        key_entry.grid(row=0, column=1, sticky="ew")
        self._attach_entry_context_menu(key_entry)
        ttk.Checkbutton(key_row, text="Save raw JSON", variable=self.save_raw_json).grid(row=0, column=2, padx=(12, 0))
        ttk.Checkbutton(key_row, text="Overwrite", variable=self.overwrite).grid(row=0, column=3, padx=(12, 0))
        ttk.Label(key_row, text="Sleep").grid(row=0, column=4, padx=(12, 4))
        ttk.Spinbox(key_row, from_=0, to=10, increment=0.25, textvariable=self.sleep_seconds, width=5).grid(row=0, column=5)

        log_frame = ttk.LabelFrame(root, text="Run log")
        log_frame.grid(row=5, column=0, sticky="nsew")
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, height=12, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        self._attach_text_context_menu(self.log_text, readonly=True)
        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=log_scroll.set)

        footer = ttk.Frame(root)
        footer.grid(row=6, column=0, sticky="ew", pady=(10, 0))
        footer.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(footer, mode="determinate")
        self.progress.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.start_button = ttk.Button(footer, text="Start transcription", command=self._start)
        self.start_button.grid(row=0, column=1, padx=(0, 8))
        self.stop_button = ttk.Button(footer, text="Stop", command=self._stop, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=2)

    def _choose_files(self) -> None:
        files = filedialog.askopenfilenames(title="Choose audio/video files", filetypes=[("Supported media", "*.mp3 *.mp4 *.mpeg *.mpga *.m4a *.wav *.webm"), ("All files", "*.*")])
        self._append_inputs(files)

    def _choose_folder(self) -> None:
        folder = filedialog.askdirectory(title="Choose folder")
        if folder:
            self._append_inputs([folder])

    def _choose_output_dir(self) -> None:
        folder = filedialog.askdirectory(initialdir=self.output_dir.get() or str(Path.home()))
        if folder:
            self.output_dir.set(folder)

    def _append_inputs(self, paths: tuple[str, ...] | list[str]) -> None:
        for item in paths:
            self.input_text.insert(tk.END, f"{item}\n")

    def _start(self) -> None:
        files, folders = self._read_input_paths()
        media_files = collect_media_files(files, folders)
        if not media_files:
            messagebox.showwarning("No media files", "Choose at least one supported media file or folder.")
            return
        output_value = self.output_dir.get().strip()
        if not output_value:
            messagebox.showwarning("No output folder", "Choose an output folder before starting transcription.")
            return
        options = TranscriptionOptions(
            output_dir=Path(output_value).expanduser(),
            model=self.model.get(),
            language=self.language.get().strip(),
            auth_mode=AUTH_LABEL_TO_MODE.get(self.auth_label.get(), "auto"),
            api_key=self.api_key.get().strip(),
            save_raw_json=self.save_raw_json.get(),
            overwrite=self.overwrite.get(),
            timeout_seconds=int(self.timeout_seconds.get()),
            sleep_seconds=float(self.sleep_seconds.get()),
        )
        self.progress.configure(maximum=len(media_files), value=0)
        self._stop_requested.clear()
        self._set_running(True)
        self._append_log(f"Starting transcription for {len(media_files)} media file(s).")
        self._worker = threading.Thread(target=self._run_worker, args=(media_files, options), daemon=True)
        self._worker.start()

    def _read_input_paths(self) -> tuple[list[Path], list[Path]]:
        files: list[Path] = []
        folders: list[Path] = []
        for line in self.input_text.get("1.0", tk.END).splitlines():
            value = line.strip().strip('"')
            if not value:
                continue
            path = Path(value).expanduser()
            folders.append(path) if path.is_dir() else files.append(path)
        return files, folders

    def _stop(self) -> None:
        self._stop_requested.set()
        self._append_log("Stop requested. Current file will finish first.")

    def _run_worker(self, media_files: list[Path], options: TranscriptionOptions) -> None:
        count = 0

        def progress(message: str) -> None:
            nonlocal count
            if message.startswith("["):
                count += 1
                self._messages.put(("progress", count - 1))
            self._messages.put(("log", message))

        try:
            results = transcribe_many(media_files, options, progress=progress, should_stop=self._stop_requested.is_set)
        except Exception as error:  # noqa: BLE001 - surface auth/setup failures in the GUI.
            self._messages.put(("log", f"FAILED -> {error}"))
            results = []
        self._messages.put(("progress", len(results)))
        self._messages.put(("done", results))

    def _poll_messages(self) -> None:
        try:
            while True:
                kind, payload = self._messages.get_nowait()
                if kind == "log":
                    self._append_log(str(payload))
                elif kind == "progress":
                    self.progress.configure(value=int(payload))
                elif kind == "done":
                    self._set_running(False)
                    results = list(payload)  # type: ignore[arg-type]
                    ok_count = sum(1 for result in results if result.ok)
                    self.progress.configure(value=len(results))
                    self._append_log(f"Done. {ok_count}/{len(results)} transcript(s) extracted.")
                    messagebox.showinfo("Transcription complete", f"{ok_count}/{len(results)} transcript(s) extracted.")
        except queue.Empty:
            pass
        self.after(100, self._poll_messages)

    def _set_running(self, running: bool) -> None:
        self.start_button.configure(state=tk.DISABLED if running else tk.NORMAL)
        self.stop_button.configure(state=tk.NORMAL if running else tk.DISABLED)

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _attach_text_context_menu(self, widget: tk.Text, *, readonly: bool) -> None:
        menu = tk.Menu(widget, tearoff=False)
        if not readonly:
            menu.add_command(label="Paste", command=lambda: self._text_event(widget, "<<Paste>>"))
            menu.add_separator()
            menu.add_command(label="Cut", command=lambda: self._text_event(widget, "<<Cut>>"))
        menu.add_command(label="Copy", command=lambda: self._text_event(widget, "<<Copy>>"))
        if not readonly:
            menu.add_command(label="Select all", command=lambda: self._select_all(widget))
        self._bind_context_menu(widget, menu)

    def _attach_entry_context_menu(self, widget: ttk.Entry) -> None:
        menu = tk.Menu(widget, tearoff=False)
        menu.add_command(label="Paste", command=lambda: widget.event_generate("<<Paste>>"))
        menu.add_command(label="Copy", command=lambda: widget.event_generate("<<Copy>>"))
        menu.add_command(label="Select all", command=lambda: widget.select_range(0, tk.END))
        self._bind_context_menu(widget, menu)

    def _bind_context_menu(self, widget: tk.Widget, menu: tk.Menu) -> None:
        def show_menu(event: tk.Event) -> str:
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()
            return "break"

        widget.bind("<Button-3>", show_menu)
        widget.bind("<Control-Button-1>", show_menu)

    def _text_event(self, widget: tk.Text, sequence: str) -> None:
        if str(widget.cget("state")) == tk.DISABLED:
            widget.configure(state=tk.NORMAL)
            try:
                widget.event_generate(sequence)
            finally:
                widget.configure(state=tk.DISABLED)
            return
        widget.event_generate(sequence)

    def _select_all(self, widget: tk.Text) -> str:
        widget.tag_add(tk.SEL, "1.0", tk.END)
        widget.mark_set(tk.INSERT, "1.0")
        widget.see(tk.INSERT)
        return "break"


def main() -> int:
    parser = argparse.ArgumentParser(description="Transcribe audio/video files into Markdown transcripts.")
    parser.add_argument("--cli", action="store_true", help="Run without the GUI.")
    parser.add_argument("--input", action="append", help="Input media file. Can be passed more than once.")
    parser.add_argument("--input-dir", action="append", help="Folder to scan recursively for media files.")
    parser.add_argument("--output-dir", default="", help="Folder for transcript Markdown files.")
    parser.add_argument("--model", choices=MODEL_CHOICES, default=TIMESTAMP_MODEL)
    parser.add_argument("--language", default="de")
    parser.add_argument("--auth-mode", choices=AUTH_MODES, default="auto")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--save-raw-json", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--sleep", type=float, default=0.0)
    args = parser.parse_args()
    if args.cli:
        if not args.output_dir:
            parser.error("--output-dir is required in --cli mode.")
        return main_cli(args)
    AudioTranscriptionApp().mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
