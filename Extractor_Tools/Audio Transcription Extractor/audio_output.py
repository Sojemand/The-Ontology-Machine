from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from audio_types import AuthMaterial, TranscriptionOptions


def render_markdown(source_path: Path, response: dict[str, Any], options: TranscriptionOptions, auth: AuthMaterial) -> str:
    text = str(response.get("text") or "").strip()
    segments = response.get("segments")
    file_hash = sha256_file(source_path)
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    frontmatter = {
        "source_file": source_path.name,
        "source_type": "audio_transcript",
        "transcript_source": "openai_audio_transcriptions",
        "model": options.model,
        "language": options.language.strip() or "",
        "auth_source": auth.source,
        "file_hash": f"sha256:{file_hash}",
        "content_hash": f"sha256:{content_hash}",
        "transcribed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    lines = ["---"]
    for key, value in frontmatter.items():
        lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    lines.extend(["---", "", f"# {source_path.stem}", "", "## Transcript", ""])
    lines.extend(_transcript_lines(text, segments))
    return "\n".join(lines)


def output_markdown_path(source_path: Path, output_dir: Path) -> Path:
    stem = sanitize_filename(source_path.stem)[:88].strip("._-") or "audio"
    digest = sha256_file_head(source_path)[:10]
    return output_dir / f"{stem}_{digest}.md"


def sanitize_filename(value: str) -> str:
    sanitized = re.sub(r"[<>:\"/\\|?*\x00-\x1f]+", "_", value)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    return sanitized.rstrip(". ")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_file_head(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        digest.update(handle.read(1024 * 1024))
    digest.update(str(path.stat().st_size).encode("ascii"))
    return digest.hexdigest()


def _transcript_lines(text: str, segments: Any) -> list[str]:
    lines: list[str] = []
    if isinstance(segments, list) and segments:
        for segment in segments:
            if not isinstance(segment, dict):
                continue
            segment_text = str(segment.get("text") or "").strip()
            if not segment_text:
                continue
            lines.append(f"[{_format_time(segment.get('start'))} - {_format_time(segment.get('end'))}] {segment_text}")
            lines.append("")
    elif text:
        lines.extend([text, ""])
    else:
        lines.extend(["_No transcript text was returned._", ""])
    return lines


def _format_time(value: Any) -> str:
    try:
        total_ms = int(round(float(value) * 1000))
    except (TypeError, ValueError):
        total_ms = 0
    seconds, ms = divmod(max(total_ms, 0), 1000)
    minutes, second = divmod(seconds, 60)
    hours, minute = divmod(minutes, 60)
    return f"{hours:02d}:{minute:02d}:{second:02d}.{ms:03d}"
