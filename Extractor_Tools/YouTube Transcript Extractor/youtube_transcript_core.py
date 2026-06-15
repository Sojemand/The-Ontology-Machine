from __future__ import annotations

# cspell:words autonumbering dedupe noplaylist sublangs ytdlp

import csv
import hashlib
import html
import json
import re
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from os import environ
from pathlib import Path
from typing import Any, Callable


USER_AGENT = "OntologyMachineYouTubeTranscriptExtractor/1.0 (+local transcript tool)"
PATH_BUDGET = 240
DEFAULT_COOKIES_FILENAME = "cookies.txt"
COOKIE_MODES = {"auto", "none", "brave", "edge", "chrome", "firefox", "file"}
COOKIE_BROWSER_MODES = {"brave", "edge", "chrome", "firefox"}
COOKIE_BROWSER_LABELS = {
    "brave": "Brave",
    "edge": "Edge",
    "chrome": "Chrome",
    "firefox": "Firefox",
}
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


class _QuietYdlLogger:
    def debug(self, message: str) -> None:
        del message

    def warning(self, message: str) -> None:
        del message

    def error(self, message: str) -> None:
        del message


@dataclass(frozen=True)
class TranscriptOptions:
    output_dir: Path
    language: str = "de"
    allow_auto_subtitles: bool = True
    save_raw_subtitles: bool = True
    overwrite: bool = False
    sleep_seconds: float = 0.5
    cookie_mode: str = "auto"
    cookies_file: Path | None = None


@dataclass(frozen=True)
class TranscriptSegment:
    start: str
    end: str
    text: str


@dataclass(frozen=True)
class Transcript:
    url: str
    video_id: str
    title: str
    channel: str | None
    published_at: str | None
    duration_seconds: int | None
    language: str
    subtitle_source: str
    subtitle_ext: str
    raw_subtitles: str
    segments: list[TranscriptSegment]


@dataclass(frozen=True)
class TranscriptResult:
    ok: bool
    url: str
    output_path: Path | None = None
    title: str | None = None
    error: str | None = None
    subtitle_source: str | None = None
    content_hash: str | None = None


def default_cookie_options(base_dir: Path | None = None) -> tuple[str, Path | None]:
    cookie_path = local_cookies_file(base_dir)
    if cookie_path.exists() and cookie_path.is_file():
        return "auto", cookie_path
    return "auto", None


def local_cookies_file(base_dir: Path | None = None) -> Path:
    root = base_dir if base_dir is not None else Path(__file__).resolve().parent
    return root / DEFAULT_COOKIES_FILENAME


def parse_urls(text: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r"https?://[^\s<>\"]+", text):
        url = match.group(0).rstrip(".,);]")
        key = url.lower()
        if key not in seen:
            seen.add(key)
            urls.append(url)
    return urls


def extract_many(
    urls: list[str],
    options: TranscriptOptions,
    *,
    progress: Callable[[str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> list[TranscriptResult]:
    options.output_dir.mkdir(parents=True, exist_ok=True)
    results: list[TranscriptResult] = []
    for index, url in enumerate(urls, start=1):
        if should_stop and should_stop():
            _log(progress, "Stopped by user.")
            break
        _log(progress, f"[{index}/{len(urls)}] Reading subtitles for {url}")
        result = extract_one(url, options)
        results.append(result)
        if result.ok:
            _log(progress, f"  OK -> {result.output_path}")
        else:
            _log(progress, f"  FAILED -> {result.error}")
        if index < len(urls) and options.sleep_seconds > 0:
            time.sleep(options.sleep_seconds)
    write_run_reports(options.output_dir, results)
    return results


def extract_one(url: str, options: TranscriptOptions) -> TranscriptResult:
    errors: list[str] = []
    for attempt in _cookie_attempts(options):
        result = _extract_one_attempt(url, attempt)
        if result.ok:
            return result
        if result.error:
            errors.append(result.error)
        if not _should_continue_after_error(result.error or ""):
            break
    return TranscriptResult(ok=False, url=url, error=_combined_failure(errors))


def _extract_one_attempt(url: str, options: TranscriptOptions) -> TranscriptResult:
    try:
        yt_dlp = _import_yt_dlp()
        with yt_dlp.YoutubeDL(_ydl_options(options)) as ydl:
            info = _load_video_info(url, ydl)
            transcript = _transcript_from_info(url, info, options, ydl)
        if not transcript.segments:
            raise ValueError("Subtitle file did not contain readable transcript segments.")
        path = write_transcript(transcript, options)
        return TranscriptResult(
            ok=True,
            url=url,
            output_path=path,
            title=transcript.title,
            subtitle_source=transcript.subtitle_source,
            content_hash="sha256:" + sha256_text(transcript_text(transcript.segments)),
        )
    except Exception as exc:  # noqa: BLE001 - batch tool should keep going per URL.
        return TranscriptResult(ok=False, url=url, error=_friendly_error(exc, options))


def _cookie_attempts(options: TranscriptOptions) -> list[TranscriptOptions]:
    cookie_mode = options.cookie_mode.lower().strip() or "auto"
    if cookie_mode != "auto":
        return [options]
    attempts = [
        _replace_cookie_options(options, cookie_mode="none", cookies_file=None),
    ]
    cookie_path = options.cookies_file or local_cookies_file()
    if cookie_path.exists() and cookie_path.is_file():
        attempts.append(_replace_cookie_options(options, cookie_mode="file", cookies_file=cookie_path))
        return attempts
    browser_mode = _first_available_browser_cookie_mode()
    if browser_mode:
        attempts.append(_replace_cookie_options(options, cookie_mode=browser_mode, cookies_file=None))
    return attempts


def _replace_cookie_options(options: TranscriptOptions, *, cookie_mode: str, cookies_file: Path | None) -> TranscriptOptions:
    return TranscriptOptions(
        output_dir=options.output_dir,
        language=options.language,
        allow_auto_subtitles=options.allow_auto_subtitles,
        save_raw_subtitles=options.save_raw_subtitles,
        overwrite=options.overwrite,
        sleep_seconds=options.sleep_seconds,
        cookie_mode=cookie_mode,
        cookies_file=cookies_file,
    )


def _first_available_browser_cookie_mode() -> str | None:
    for mode in ("brave", "edge", "chrome", "firefox"):
        if _browser_cookie_store_exists(mode):
            return mode
    return None


def _browser_cookie_store_exists(mode: str) -> bool:
    local_appdata = Path(environ.get("LOCALAPPDATA", ""))
    appdata = Path(environ.get("APPDATA", ""))
    roots: dict[str, tuple[Path, str]] = {
        "brave": (local_appdata / "BraveSoftware" / "Brave-Browser" / "User Data", "*/Network/Cookies"),
        "edge": (local_appdata / "Microsoft" / "Edge" / "User Data", "*/Network/Cookies"),
        "chrome": (local_appdata / "Google" / "Chrome" / "User Data", "*/Network/Cookies"),
        "firefox": (appdata / "Mozilla" / "Firefox" / "Profiles", "*/cookies.sqlite"),
    }
    root_pattern = roots.get(mode)
    if root_pattern is None:
        return False
    root, pattern = root_pattern
    return root.exists() and any(root.glob(pattern))


def _should_continue_after_error(error: str) -> bool:
    lower = error.lower()
    return "http 429" in lower or "too many requests" in lower


def _combined_failure(errors: list[str]) -> str:
    if not errors:
        return "Transcript extraction failed."
    if len(errors) == 1:
        return errors[0]
    if "cookie database" in errors[-1].lower():
        return errors[-1]
    return errors[-1] + " Previous attempt: " + errors[0]


def _import_yt_dlp() -> Any:
    try:
        import yt_dlp  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001 - user-facing dependency diagnostic.
        raise RuntimeError('yt-dlp is not installed. Run "Install yt-dlp.bat" in this folder first.') from exc
    return yt_dlp


def _ydl_options(options: TranscriptOptions) -> dict[str, Any]:
    cookie_mode = options.cookie_mode.lower().strip() or "none"
    if cookie_mode not in COOKIE_MODES:
        raise RuntimeError(f"Unsupported cookie mode: {options.cookie_mode}")
    ydl_options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "socket_timeout": 60,
        "logger": _QuietYdlLogger(),
        "http_headers": {"User-Agent": USER_AGENT},
    }
    if cookie_mode in COOKIE_BROWSER_MODES:
        ydl_options["cookiesfrombrowser"] = (cookie_mode,)
    if cookie_mode == "file":
        if options.cookies_file is None:
            raise RuntimeError("Cookie mode is cookies.txt file, but no cookie file was selected.")
        cookie_path = options.cookies_file.expanduser()
        if not cookie_path.exists():
            raise RuntimeError(f"Cookie file does not exist: {cookie_path}")
        ydl_options["cookiefile"] = str(cookie_path)
    return ydl_options


def _load_video_info(url: str, ydl: Any) -> dict[str, Any]:
    info = ydl.extract_info(url, download=False)
    if not isinstance(info, dict):
        raise RuntimeError("yt-dlp did not return video metadata.")
    if info.get("_type") in {"playlist", "multi_video"}:
        raise RuntimeError("Paste individual video URLs, not playlists.")
    return info


def _transcript_from_info(url: str, info: dict[str, Any], options: TranscriptOptions, ydl: Any) -> Transcript:
    language, source, subtitle = _select_subtitle(info, options.language, options.allow_auto_subtitles)
    ext = str(subtitle.get("ext") or "").lower()
    subtitle_url = str(subtitle.get("url") or "")
    if not subtitle_url:
        raise RuntimeError("Selected subtitle entry has no download URL.")
    raw_subtitles = _fetch_subtitle_text(subtitle_url, ydl)
    segments = _parse_subtitle_text(raw_subtitles, ext)
    return Transcript(
        url=str(info.get("webpage_url") or url),
        video_id=str(info.get("id") or sha256_text(url)[:12]),
        title=clean_text(str(info.get("title") or "YouTube transcript")),
        channel=_optional_clean(info.get("channel") or info.get("uploader")),
        published_at=_publication_date(info),
        duration_seconds=_optional_int(info.get("duration")),
        language=language,
        subtitle_source=source,
        subtitle_ext=ext or "unknown",
        raw_subtitles=raw_subtitles,
        segments=segments,
    )


def _select_subtitle(info: dict[str, Any], requested_language: str, allow_auto: bool) -> tuple[str, str, dict[str, Any]]:
    requested = requested_language.strip() or "de"
    subtitles = info.get("subtitles") if isinstance(info.get("subtitles"), dict) else {}
    selected = _select_language_entry(subtitles, requested)
    if selected is not None:
        language, entry = selected
        return language, "youtube_subtitles", entry

    if allow_auto:
        auto = info.get("automatic_captions") if isinstance(info.get("automatic_captions"), dict) else {}
        selected = _select_language_entry(auto, requested)
        if selected is not None:
            language, entry = selected
            return language, "youtube_auto_subtitles", entry

    auto_map = info.get("automatic_captions") if isinstance(info.get("automatic_captions"), dict) else {}
    available = sorted(str(key) for key in {**subtitles, **auto_map}.keys())
    suffix = f" Available languages: {', '.join(available[:25])}" if available else " No subtitle languages were listed."
    raise RuntimeError(f"No subtitles found for language '{requested}'.{suffix}")


def _select_language_entry(subtitle_map: dict[str, Any], requested: str) -> tuple[str, dict[str, Any]] | None:
    language = _find_language_key(subtitle_map, requested)
    if language is None:
        return None
    entries = subtitle_map.get(language)
    if not isinstance(entries, list):
        return None
    for preferred_ext in ("vtt", "json3", "ttml", "srv3"):
        for entry in entries:
            if isinstance(entry, dict) and str(entry.get("ext") or "").lower() == preferred_ext:
                return language, entry
    for entry in entries:
        if isinstance(entry, dict):
            return language, entry
    return None


def _find_language_key(subtitle_map: dict[str, Any], requested: str) -> str | None:
    normalized = requested.strip().lower()
    for key in subtitle_map:
        if str(key).lower() == normalized:
            return str(key)
    for key in subtitle_map:
        if str(key).lower().startswith(normalized + "-"):
            return str(key)
    for key in subtitle_map:
        if str(key).lower().startswith(normalized):
            return str(key)
    return None


def _fetch_subtitle_text(url: str, ydl: Any) -> str:
    response = ydl.urlopen(url)
    try:
        data = response.read()
    finally:
        close = getattr(response, "close", None)
        if callable(close):
            close()
    return data.decode("utf-8", errors="replace")


def _parse_subtitle_text(payload: str, ext: str) -> list[TranscriptSegment]:
    if ext == "json3":
        return _parse_json3(payload)
    return _parse_vtt_like(payload)


def _parse_json3(payload: str) -> list[TranscriptSegment]:
    data = json.loads(payload)
    events = data.get("events") if isinstance(data, dict) else None
    if not isinstance(events, list):
        return []
    segments: list[TranscriptSegment] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        parts = event.get("segs")
        if not isinstance(parts, list):
            continue
        text = clean_text("".join(str(part.get("utf8") or "") for part in parts if isinstance(part, dict)))
        if not text:
            continue
        start_ms = _optional_int(event.get("tStartMs")) or 0
        end_ms = start_ms + (_optional_int(event.get("dDurationMs")) or 0)
        _append_segment(segments, format_ms(start_ms), format_ms(end_ms), text)
    return segments


def _parse_vtt_like(payload: str) -> list[TranscriptSegment]:
    lines = payload.replace("\ufeff", "").splitlines()
    segments: list[TranscriptSegment] = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line or line == "WEBVTT":
            index += 1
            continue
        if line.startswith(("NOTE", "STYLE", "REGION")):
            index = _skip_until_blank(lines, index + 1)
            continue
        if "-->" not in line and index + 1 < len(lines) and "-->" in lines[index + 1]:
            index += 1
            line = lines[index].strip()
        if "-->" not in line:
            index += 1
            continue
        start, end = _parse_vtt_timestamp_line(line)
        index += 1
        text_lines: list[str] = []
        while index < len(lines) and lines[index].strip():
            text_lines.append(lines[index].strip())
            index += 1
        text = clean_caption_text(" ".join(text_lines))
        if text:
            _append_segment(segments, start, end, text)
    return segments


def _skip_until_blank(lines: list[str], index: int) -> int:
    while index < len(lines) and lines[index].strip():
        index += 1
    return index


def _parse_vtt_timestamp_line(line: str) -> tuple[str, str]:
    left, right = line.split("-->", 1)
    start = left.strip()
    end = right.strip().split()[0]
    return normalize_timestamp(start), normalize_timestamp(end)


def normalize_timestamp(value: str) -> str:
    parts = value.replace(",", ".").split(":")
    if len(parts) == 2:
        return f"00:{parts[0].zfill(2)}:{parts[1]}"
    if len(parts) == 3:
        return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:{parts[2]}"
    return value


def clean_caption_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    text = html.unescape(text)
    text = text.replace("\u266a", " ")
    return clean_text(text)


def _append_segment(segments: list[TranscriptSegment], start: str, end: str, text: str) -> None:
    if segments and segments[-1].text == text:
        return
    segments.append(TranscriptSegment(start=start, end=end, text=text))


def write_transcript(transcript: Transcript, options: TranscriptOptions) -> Path:
    options.output_dir.mkdir(parents=True, exist_ok=True)
    stem = safe_file_stem(transcript.published_at, transcript.title, transcript.video_id, options.output_dir)
    path = _unique_path(options.output_dir / f"{stem}.md", overwrite=options.overwrite)
    raw_path: Path | None = None
    if options.save_raw_subtitles:
        raw_dir = options.output_dir / "raw_subtitles"
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_path = _unique_path(raw_dir / f"{stem}.{transcript.language}.{transcript.subtitle_ext or 'txt'}", overwrite=options.overwrite)
        raw_path.write_text(transcript.raw_subtitles, encoding="utf-8")
    path.write_text(render_markdown(transcript, raw_path=raw_path), encoding="utf-8")
    return path


def render_markdown(transcript: Transcript, *, raw_path: Path | None) -> str:
    content = transcript_text(transcript.segments)
    frontmatter = {
        "source_url": transcript.url,
        "source_platform": "youtube",
        "source_channel": transcript.channel,
        "title": transcript.title,
        "published_at": transcript.published_at,
        "duration_seconds": transcript.duration_seconds,
        "video_id": transcript.video_id,
        "transcript_source": transcript.subtitle_source,
        "subtitle_language": transcript.language,
        "url_hash": "sha256:" + sha256_text(transcript.url),
        "content_hash": "sha256:" + sha256_text(content),
        "extractor": "yt-dlp-subtitles",
        "raw_subtitles_path": str(raw_path) if raw_path else None,
    }
    lines = ["---"]
    lines.extend(f"{key}: {_yaml_value(value)}" for key, value in frontmatter.items())
    lines.extend(["---", "", f"# {transcript.title}", "", "## Transcript", "", content, ""])
    return "\n".join(lines)


def transcript_text(segments: list[TranscriptSegment]) -> str:
    return "\n".join(f"[{segment.start} - {segment.end}] {segment.text}" for segment in segments)


def write_run_reports(output_dir: Path, results: list[TranscriptResult]) -> None:
    report_path = output_dir / "transcript_report.csv"
    with report_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["ok", "url", "title", "output_path", "subtitle_source", "content_hash", "error"],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "ok": result.ok,
                    "url": result.url,
                    "title": result.title or "",
                    "output_path": str(result.output_path or ""),
                    "subtitle_source": result.subtitle_source or "",
                    "content_hash": result.content_hash or "",
                    "error": result.error or "",
                }
            )
    failed = [result for result in results if not result.ok]
    if not failed:
        failed_path = output_dir / "failed_urls.csv"
        if failed_path.exists():
            failed_path.unlink()
        return
    with (output_dir / "failed_urls.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["url", "error"])
        writer.writeheader()
        for result in failed:
            writer.writerow({"url": result.url, "error": result.error or ""})


def safe_file_stem(published_at: str | None, title: str, video_id: str, output_dir: Path) -> str:
    parts = [part for part in [published_at, title, video_id] if part]
    stem = slugify("_".join(parts)) or f"youtube_{sha256_text(video_id)[:10]}"
    budget = PATH_BUDGET - len(str(output_dir)) - len(".md") - 1
    budget = max(32, min(120, budget))
    return stem[:budget].strip("._-") or "youtube_transcript"


def _unique_path(path: Path, *, overwrite: bool) -> Path:
    if overwrite or not path.exists():
        return path
    for index in range(2, 10_000):
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not create unique output path for {path}")


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", ascii_text).strip("._-").lower()
    return re.sub(r"_+", "_", text)


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _optional_clean(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = clean_text(str(value))
    return text or None


def _publication_date(info: dict[str, Any]) -> str | None:
    upload_date = info.get("upload_date")
    if isinstance(upload_date, str) and re.fullmatch(r"\d{8}", upload_date):
        return f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
    timestamp = _optional_int(info.get("timestamp"))
    if timestamp is not None:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()
    return None


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def format_ms(value: int) -> str:
    milliseconds = max(0, value)
    seconds, ms = divmod(milliseconds, 1000)
    minutes, sec = divmod(seconds, 60)
    hours, minute = divmod(minutes, 60)
    return f"{hours:02d}:{minute:02d}:{sec:02d}.{ms:03d}"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _yaml_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def _log(progress: Callable[[str], None] | None, message: str) -> None:
    if progress:
        progress(message)


def _friendly_error(exc: Exception, options: TranscriptOptions) -> str:
    message = _strip_terminal_markup(str(exc)).strip()
    lower = message.lower()
    cookie_mode = options.cookie_mode.lower().strip() or "none"
    if "could not find" in lower and "cookies database" in lower and cookie_mode in COOKIE_BROWSER_MODES:
        label = COOKIE_BROWSER_LABELS.get(cookie_mode, cookie_mode)
        hint = (
            f"Cookie mode is set to {label}, but yt-dlp could not find a {label} cookie database. "
            "Choose the browser you actually use for YouTube, or use a cookies.txt file."
        )
        if cookie_mode == "chrome":
            hint += " If you use Brave, choose Cookie mode = Brave."
        return f"{hint} Original diagnostic: {message}"
    if "could not copy chrome cookie database" in lower and cookie_mode in COOKIE_BROWSER_MODES:
        label = COOKIE_BROWSER_LABELS.get(cookie_mode, cookie_mode)
        return (
            f"Cookie mode is set to {label}, but yt-dlp could not copy the Chromium cookie database. "
            f"Close {label} completely, including background processes, then retry. "
            "Advanced fallback: use a cookies.txt file. "
            "Original diagnostic: " + message
        )
    if "http error 429" in lower or "too many requests" in lower:
        return (
            "YouTube returned HTTP 429 (Too Many Requests). For auto subtitles, try the browser cookie mode "
            "for the browser you use for YouTube, for example Brave, Edge, Chrome, or Firefox."
        )
    return message


def _strip_terminal_markup(value: str) -> str:
    text = _ANSI_ESCAPE_RE.sub("", value)
    text = text.replace("ERROR:", "").strip()
    return clean_text(text)
