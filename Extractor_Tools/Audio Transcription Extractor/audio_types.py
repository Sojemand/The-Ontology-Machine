from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


OPENAI_TRANSCRIPTION_URL = "https://api.openai.com/v1/audio/transcriptions"
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
SUPPORTED_EXTENSIONS = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm"}
TIMESTAMP_MODEL = "whisper-1"
MODEL_CHOICES = ("whisper-1", "gpt-4o-transcribe", "gpt-4o-mini-transcribe")
AUTH_MODES = ("auto", "api_key", "frontend_oauth")


@dataclass(frozen=True)
class TranscriptionOptions:
    output_dir: Path
    model: str = TIMESTAMP_MODEL
    language: str = "de"
    auth_mode: str = "auto"
    api_key: str = ""
    save_raw_json: bool = True
    overwrite: bool = False
    timeout_seconds: int = 600
    sleep_seconds: float = 0.0


@dataclass(frozen=True)
class AuthMaterial:
    bearer_token: str
    source: str
    note: str = ""


@dataclass(frozen=True)
class TranscriptionResult:
    source_path: Path
    ok: bool
    output_path: Path | None = None
    raw_output_path: Path | None = None
    error: str = ""
    auth_source: str = ""
    model: str = ""
