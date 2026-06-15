from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Callable

from audio_auth import looks_like_auth_failure, oauth_rejection_message, resolve_auth
from audio_openai_client import call_openai_transcription
from audio_output import output_markdown_path, render_markdown
from audio_types import (
    AUTH_MODES,
    MAX_UPLOAD_BYTES,
    MODEL_CHOICES,
    SUPPORTED_EXTENSIONS,
    TIMESTAMP_MODEL,
    AuthMaterial,
    TranscriptionOptions,
    TranscriptionResult,
)


def collect_media_files(files: list[Path], folders: list[Path]) -> list[Path]:
    collected: list[Path] = []
    for file_path in files:
        path = file_path.expanduser()
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            collected.append(path)
    for folder in folders:
        root = folder.expanduser()
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                collected.append(path)
    unique: dict[str, Path] = {}
    for path in collected:
        try:
            key = str(path.resolve()).lower()
        except OSError:
            key = str(path.absolute()).lower()
        unique[key] = path
    return sorted(unique.values(), key=lambda item: str(item).lower())


def transcribe_many(
    media_files: list[Path],
    options: TranscriptionOptions,
    *,
    progress: Callable[[str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> list[TranscriptionResult]:
    options.output_dir.mkdir(parents=True, exist_ok=True)
    results: list[TranscriptionResult] = []
    auth = resolve_auth(options)
    if progress:
        progress(f"Credential source: {auth.source}.")
        if auth.note:
            progress(auth.note)

    total = len(media_files)
    for index, source_path in enumerate(media_files, start=1):
        if should_stop and should_stop():
            if progress:
                progress("Stop requested. No further files will be submitted.")
            break
        if progress:
            progress(f"[{index}/{total}] Transcribing {source_path.name}")
        result = transcribe_one(source_path, options, auth)
        results.append(result)
        if progress:
            progress(f"  OK -> {result.output_path}" if result.ok else f"  FAILED -> {result.error}")
        if options.sleep_seconds > 0 and index < total:
            time.sleep(options.sleep_seconds)
    return results


def transcribe_one(source_path: Path, options: TranscriptionOptions, auth: AuthMaterial) -> TranscriptionResult:
    try:
        path = source_path.expanduser()
        _validate_source_file(path)
        output_path = output_markdown_path(path, options.output_dir)
        raw_path = output_path.with_suffix(".raw.json")
        if output_path.exists() and not options.overwrite:
            raw_result = raw_path if raw_path.exists() else None
            return TranscriptionResult(path, True, output_path, raw_result, auth_source=auth.source, model=options.model)

        response = call_openai_transcription(path, options, auth)
        output_path.write_text(render_markdown(path, response, options, auth), encoding="utf-8")
        written_raw = _write_raw_json(raw_path, response) if options.save_raw_json else None
        return TranscriptionResult(path, True, output_path, written_raw, auth_source=auth.source, model=options.model)
    except Exception as error:  # noqa: BLE001 - batch extraction should continue through individual failures.
        message = str(error)
        if auth.source == "frontend_oauth" and looks_like_auth_failure(message):
            message = oauth_rejection_message(message)
        return TranscriptionResult(source_path, False, error=message, auth_source=auth.source, model=options.model)


def parse_cli_paths(args: argparse.Namespace) -> list[Path]:
    files = [Path(item) for item in args.input or []]
    folders = [Path(item) for item in args.input_dir or []]
    return collect_media_files(files, folders)


def main_cli(args: argparse.Namespace) -> int:
    media_files = parse_cli_paths(args)
    if not media_files:
        print("No supported media files found.")
        return 2
    options = TranscriptionOptions(
        output_dir=Path(args.output_dir),
        model=args.model,
        language=args.language,
        auth_mode=args.auth_mode,
        api_key=args.api_key or "",
        save_raw_json=args.save_raw_json,
        overwrite=args.overwrite,
        timeout_seconds=args.timeout,
        sleep_seconds=args.sleep,
    )
    results = transcribe_many(media_files, options, progress=print)
    return 0 if all(result.ok for result in results) else 1


def _validate_source_file(path: Path) -> None:
    if not path.is_file():
        raise RuntimeError("File does not exist.")
    extension = path.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise RuntimeError(f"Unsupported media type: {extension or '<none>'}. Supported: {supported}.")
    size = path.stat().st_size
    if size <= 0:
        raise RuntimeError("File is empty.")
    if size > MAX_UPLOAD_BYTES:
        mb = size / (1024 * 1024)
        raise RuntimeError(
            f"File is {mb:.1f} MB. The OpenAI Audio upload limit is 25 MB. "
            "Compress or split the media before submitting it."
        )


def _write_raw_json(raw_path: Path, response: dict) -> Path:
    raw_path.write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
    return raw_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcribe audio/video media files into Markdown transcripts.")
    parser.add_argument("--input", action="append", help="Input media file. Can be passed more than once.")
    parser.add_argument("--input-dir", action="append", help="Folder to scan recursively for supported media files.")
    parser.add_argument("--output-dir", required=True, help="Folder for transcript Markdown files.")
    parser.add_argument("--model", choices=MODEL_CHOICES, default=TIMESTAMP_MODEL)
    parser.add_argument("--language", default="de", help="Optional language code such as de or en.")
    parser.add_argument("--auth-mode", choices=AUTH_MODES, default="auto")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--save-raw-json", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--sleep", type=float, default=0.0)
    sys.exit(main_cli(parser.parse_args()))
