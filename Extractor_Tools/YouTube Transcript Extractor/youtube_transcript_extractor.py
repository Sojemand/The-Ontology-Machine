from __future__ import annotations

# cspell:words initialdir padx pady textvariable yscrollcommand

import argparse
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from youtube_transcript_core import TranscriptOptions, default_cookie_options, extract_many, parse_urls


COOKIE_LABEL_TO_MODE = {
    "Auto (recommended)": "auto",
    "No cookies": "none",
    "Brave": "brave",
    "Edge": "edge",
    "Chrome": "chrome",
    "Firefox": "firefox",
    "cookies.txt file": "file",
}
COOKIE_MODE_TO_LABEL = {value: key for key, value in COOKIE_LABEL_TO_MODE.items()}


class YouTubeTranscriptApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("YouTube Transcript Extractor")
        self.geometry("900x680")
        self.minsize(760, 560)
        self._messages: queue.Queue[tuple[str, object]] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._stop_requested = threading.Event()
        self.output_dir = tk.StringVar(value="")
        self.language = tk.StringVar(value="de")
        self.allow_auto_subtitles = tk.BooleanVar(value=True)
        self.save_raw_subtitles = tk.BooleanVar(value=True)
        self.overwrite = tk.BooleanVar(value=False)
        self.sleep_seconds = tk.DoubleVar(value=0.5)
        cookie_mode, cookies_file = default_cookie_options()
        self.cookie_label = tk.StringVar(value=COOKIE_MODE_TO_LABEL[cookie_mode])
        self.cookies_file = tk.StringVar(value=str(cookies_file or ""))
        self._build_ui()
        self.after(100, self._poll_messages)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)
        root.rowconfigure(5, weight=1)

        header = ttk.Label(root, text="Paste YouTube video URLs, choose an output folder, then extract subtitle transcripts.", font=("", 11, "bold"))
        header.grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.url_text = tk.Text(root, height=12, wrap=tk.WORD, undo=True)
        self.url_text.grid(row=1, column=0, sticky="nsew")
        self._attach_text_context_menu(self.url_text, readonly=False)

        options = ttk.Frame(root)
        options.grid(row=2, column=0, sticky="ew", pady=10)
        options.columnconfigure(1, weight=1)
        ttk.Label(options, text="Output folder").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(options, textvariable=self.output_dir).grid(row=0, column=1, sticky="ew")
        ttk.Button(options, text="Choose...", command=self._choose_output_dir).grid(row=0, column=2, padx=(8, 0))

        checks = ttk.Frame(root)
        checks.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(checks, text="Language").pack(side=tk.LEFT)
        ttk.Entry(checks, textvariable=self.language, width=7).pack(side=tk.LEFT, padx=(4, 16))
        ttk.Checkbutton(checks, text="Use auto subtitles if needed", variable=self.allow_auto_subtitles).pack(side=tk.LEFT, padx=(0, 16))
        ttk.Checkbutton(checks, text="Save raw subtitles", variable=self.save_raw_subtitles).pack(side=tk.LEFT, padx=(0, 16))
        ttk.Checkbutton(checks, text="Overwrite existing files", variable=self.overwrite).pack(side=tk.LEFT, padx=(0, 16))
        ttk.Label(checks, text="Sleep").pack(side=tk.LEFT)
        ttk.Spinbox(checks, from_=0, to=10, increment=0.25, textvariable=self.sleep_seconds, width=5).pack(side=tk.LEFT, padx=(4, 0))

        cookies = ttk.Frame(root)
        cookies.grid(row=4, column=0, sticky="ew", pady=(0, 8))
        cookies.columnconfigure(3, weight=1)
        ttk.Label(cookies, text="Cookie mode").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.cookie_combo = ttk.Combobox(
            cookies,
            textvariable=self.cookie_label,
            values=list(COOKIE_LABEL_TO_MODE.keys()),
            state="readonly",
            width=18,
        )
        self.cookie_combo.grid(row=0, column=1, sticky="w", padx=(0, 12))
        self.cookie_combo.bind("<<ComboboxSelected>>", lambda _event: self._sync_cookie_file_state())
        ttk.Label(cookies, text="Cookie file").grid(row=0, column=2, sticky="w", padx=(0, 8))
        self.cookies_entry = ttk.Entry(cookies, textvariable=self.cookies_file)
        self.cookies_entry.grid(row=0, column=3, sticky="ew")
        self.cookies_button = ttk.Button(cookies, text="Choose...", command=self._choose_cookies_file)
        self.cookies_button.grid(row=0, column=4, padx=(8, 0))
        ttk.Button(cookies, text="Cookie help", command=self._show_cookie_help).grid(row=0, column=5, padx=(8, 0))
        ttk.Label(
            cookies,
            text="Auto tries standard access first, then local cookies.txt or your detected browser session if YouTube blocks auto subtitles.",
        ).grid(
            row=1,
            column=1,
            columnspan=4,
            sticky="w",
            pady=(4, 0),
        )
        self._sync_cookie_file_state()

        log_frame = ttk.LabelFrame(root, text="Run log")
        log_frame.grid(row=5, column=0, sticky="nsew")
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, height=12, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        self._attach_text_context_menu(self.log_text, readonly=True)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

        footer = ttk.Frame(root)
        footer.grid(row=6, column=0, sticky="ew", pady=(10, 0))
        footer.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(footer, mode="determinate")
        self.progress.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.start_button = ttk.Button(footer, text="Start extraction", command=self._start)
        self.start_button.grid(row=0, column=1, padx=(0, 8))
        self.stop_button = ttk.Button(footer, text="Stop", command=self._stop, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=2)

    def _choose_output_dir(self) -> None:
        folder = filedialog.askdirectory(initialdir=self.output_dir.get() or str(Path.home()))
        if folder:
            self.output_dir.set(folder)

    def _choose_cookies_file(self) -> None:
        file_path = filedialog.askopenfilename(
            initialdir=str(Path(self.cookies_file.get()).parent) if self.cookies_file.get().strip() else str(Path.home()),
            title="Choose cookies.txt",
            filetypes=[("Cookie files", "*.txt"), ("All files", "*.*")],
        )
        if file_path:
            self.cookies_file.set(file_path)

    def _show_cookie_help(self) -> None:
        messagebox.showinfo(
            "Cookie help",
            (
                "Auto mode first tries normal subtitle access. If YouTube blocks auto subtitles, it tries a local cookies.txt "
                "or a detected browser session.\n\n"
                "cookies.txt is an exported copy of your browser's YouTube cookies in Netscape cookie-file format.\n\n"
                "The extractor cannot ship a real cookies.txt because real cookies are private login/session data.\n\n"
                "For the simple flow, export cookies from the browser you use for YouTube, name the file cookies.txt, "
                "and put it directly into the YouTube Transcript Extractor folder, next to the start BAT and README.\n\n"
                "When that file exists in this folder, the extractor selects it automatically at startup. "
                "You can also use the Cookie file picker manually."
            ),
        )

    def _sync_cookie_file_state(self) -> None:
        state = tk.NORMAL if self._cookie_mode() == "file" else tk.DISABLED
        self.cookies_entry.configure(state=state)
        self.cookies_button.configure(state=state)

    def _cookie_mode(self) -> str:
        return COOKIE_LABEL_TO_MODE.get(self.cookie_label.get(), "none")

    def _attach_text_context_menu(self, widget: tk.Text, *, readonly: bool) -> None:
        menu = tk.Menu(widget, tearoff=False)
        if not readonly:
            menu.add_command(label="Paste", command=lambda: self._text_event(widget, "<<Paste>>"))
            menu.add_separator()
            menu.add_command(label="Cut", command=lambda: self._text_event(widget, "<<Cut>>"))
        menu.add_command(label="Copy", command=lambda: self._text_event(widget, "<<Copy>>"))
        if not readonly:
            menu.add_command(label="Select all", command=lambda: self._select_all(widget))

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

    def _start(self) -> None:
        urls = parse_urls(self.url_text.get("1.0", tk.END))
        if not urls:
            messagebox.showwarning("No URLs", "Paste at least one YouTube video URL.")
            return
        output_value = self.output_dir.get().strip()
        if not output_value:
            messagebox.showwarning("No output folder", "Choose an output folder before starting extraction.")
            return
        cookie_mode = self._cookie_mode()
        cookies_file = Path(self.cookies_file.get()).expanduser() if self.cookies_file.get().strip() else None
        if cookie_mode == "file" and cookies_file is None:
            messagebox.showwarning("No cookie file", "Choose a cookies.txt file or switch Cookie mode back to No cookies.")
            return
        options = TranscriptOptions(
            output_dir=Path(output_value).expanduser(),
            language=self.language.get().strip() or "de",
            allow_auto_subtitles=self.allow_auto_subtitles.get(),
            save_raw_subtitles=self.save_raw_subtitles.get(),
            overwrite=self.overwrite.get(),
            sleep_seconds=float(self.sleep_seconds.get()),
            cookie_mode=cookie_mode,
            cookies_file=cookies_file,
        )
        self.progress.configure(maximum=len(urls), value=0)
        self._stop_requested.clear()
        self._set_running(True)
        self._append_log(f"Starting transcript extraction for {len(urls)} URL(s).")
        self._worker = threading.Thread(target=self._run_worker, args=(urls, options), daemon=True)
        self._worker.start()

    def _stop(self) -> None:
        self._stop_requested.set()
        self._append_log("Stop requested. Current URL will finish first.")

    def _run_worker(self, urls: list[str], options: TranscriptOptions) -> None:
        count = 0

        def progress(message: str) -> None:
            nonlocal count
            if message.startswith("["):
                count += 1
                self._messages.put(("progress", count - 1))
            self._messages.put(("log", message))

        results = extract_many(urls, options, progress=progress, should_stop=self._stop_requested.is_set)
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
                    messagebox.showinfo("Extraction complete", f"{ok_count}/{len(results)} transcript(s) extracted.")
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


def run_cli(args: argparse.Namespace) -> int:
    urls_text = Path(args.urls_file).read_text(encoding="utf-8") if args.urls_file else "\n".join(args.urls or [])
    urls = parse_urls(urls_text)
    if not urls:
        print("No URLs found.")
        return 2
    cookie_mode, cookies_file = _resolve_cli_cookie_options(args)
    options = TranscriptOptions(
        output_dir=Path(args.output_dir),
        language=args.language,
        allow_auto_subtitles=args.allow_auto_subtitles,
        save_raw_subtitles=args.save_raw_subtitles,
        overwrite=args.overwrite,
        sleep_seconds=args.sleep,
        cookie_mode=cookie_mode,
        cookies_file=cookies_file,
    )
    results = extract_many(urls, options, progress=print)
    return 0 if all(result.ok for result in results) else 1


def _resolve_cli_cookie_options(args: argparse.Namespace) -> tuple[str, Path | None]:
    cookies_file = Path(args.cookies_file).expanduser() if args.cookies_file else None
    if args.cookie_mode:
        return args.cookie_mode, cookies_file
    if cookies_file is not None:
        return "file", cookies_file
    return default_cookie_options()


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract YouTube subtitles into Markdown transcript files.")
    parser.add_argument("--cli", action="store_true", help="Run without the GUI.")
    parser.add_argument("--urls-file", default=None, help="Text file containing URLs.")
    parser.add_argument("--url", dest="urls", action="append", help="URL to extract; may be repeated.")
    parser.add_argument("--output-dir", default=str(Path.cwd() / "youtube_transcripts"))
    parser.add_argument("--language", default="de")
    parser.add_argument("--no-auto-subtitles", dest="allow_auto_subtitles", action="store_false")
    parser.add_argument("--no-raw-subtitles", dest="save_raw_subtitles", action="store_false")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.5)
    parser.add_argument("--cookie-mode", choices=["auto", "none", "brave", "edge", "chrome", "firefox", "file"], default=None)
    parser.add_argument("--cookies-file", default=None)
    args = parser.parse_args()
    if args.cli:
        return run_cli(args)
    app = YouTubeTranscriptApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
