from __future__ import annotations

import http.client
import json
import mimetypes
import re
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from audio_types import MODEL_CHOICES, OPENAI_TRANSCRIPTION_URL, TIMESTAMP_MODEL, AuthMaterial, TranscriptionOptions


def call_openai_transcription(source_path: Path, options: TranscriptionOptions, auth: AuthMaterial) -> dict[str, Any]:
    model = options.model if options.model in MODEL_CHOICES else TIMESTAMP_MODEL
    fields: list[tuple[str, str]] = [("model", model), ("temperature", "0")]
    language = options.language.strip()
    if language:
        fields.append(("language", language))
    if model == TIMESTAMP_MODEL:
        fields.append(("response_format", "verbose_json"))
        fields.append(("timestamp_granularities[]", "segment"))
    else:
        fields.append(("response_format", "json"))

    file_bytes = source_path.read_bytes()
    body, content_type = build_multipart_body(fields, source_path.name, file_bytes, _content_type_for(source_path))
    request = Request(
        OPENAI_TRANSCRIPTION_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {auth.bearer_token}",
            "Content-Type": content_type,
            "Content-Length": str(len(body)),
            "User-Agent": "OntologyMachine-AudioTranscriptionExtractor/1.0",
        },
    )
    try:
        with urlopen(request, timeout=options.timeout_seconds) as response:  # noqa: S310 - fixed OpenAI endpoint.
            payload = response.read().decode("utf-8", errors="replace")
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI Audio API returned HTTP {error.code}: {_compact_api_error(detail)}") from error
    except (URLError, TimeoutError, http.client.HTTPException) as error:
        raise RuntimeError(f"OpenAI Audio API request failed: {error}") from error
    try:
        return json.loads(payload)
    except json.JSONDecodeError as error:
        raise RuntimeError("OpenAI Audio API returned non-JSON output.") from error


def build_multipart_body(fields: list[tuple[str, str]], filename: str, file_bytes: bytes, content_type: str) -> tuple[bytes, str]:
    boundary = f"----OntologyMachineAudio{uuid.uuid4().hex}"
    parts: list[bytes] = []
    for name, value in fields:
        parts.extend(
            [
                f"--{boundary}\r\n".encode("ascii"),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("ascii"),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )
    escaped_filename = filename.replace('"', "_")
    parts.extend(
        [
            f"--{boundary}\r\n".encode("ascii"),
            f'Content-Disposition: form-data; name="file"; filename="{escaped_filename}"\r\n'.encode("utf-8"),
            f"Content-Type: {content_type}\r\n\r\n".encode("ascii"),
            file_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode("ascii"),
        ]
    )
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def _content_type_for(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def _compact_api_error(detail: str) -> str:
    try:
        data = json.loads(detail)
        message = data.get("error", {}).get("message") or data.get("message")
        if message:
            return str(message)
    except json.JSONDecodeError:
        pass
    return re.sub(r"\s+", " ", detail).strip()[:1000] or "no error body"
