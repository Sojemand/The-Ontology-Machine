from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from audio_types import AUTH_MODES, AuthMaterial, TranscriptionOptions


def resolve_auth(options: TranscriptionOptions) -> AuthMaterial:
    mode = options.auth_mode if options.auth_mode in AUTH_MODES else "auto"
    manual_key = options.api_key.strip()
    if manual_key:
        return AuthMaterial(manual_key, "manual_api_key")

    env_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if env_key and mode in {"auto", "api_key"}:
        return AuthMaterial(env_key, "env_openai_api_key")

    frontend = load_frontend_auth()
    if mode == "frontend_oauth":
        token = str(frontend.get("oauth_access_token") or "").strip()
        if not token:
            raise RuntimeError(_frontend_auth_error(frontend, "No frontend OAuth access token was found."))
        return AuthMaterial(token, "frontend_oauth", "Using the frontend OAuth access token.")

    if mode in {"auto", "api_key"}:
        api_key = str(frontend.get("api_key") or "").strip()
        if api_key:
            return AuthMaterial(api_key, "frontend_saved_api_key")
        if mode == "api_key":
            raise RuntimeError(_frontend_auth_error(frontend, "No API key was found in the frontend credential store."))

    if mode == "auto":
        token = str(frontend.get("oauth_access_token") or "").strip()
        if token:
            return AuthMaterial(
                token,
                "frontend_oauth",
                "Using frontend OAuth as a last resort. If the Audio endpoint rejects it, use an API key.",
            )

    raise RuntimeError(
        "No OpenAI credential was found. Set OPENAI_API_KEY, save an API key in the Client Frontend, "
        "paste an API key into this tool, or choose Frontend OAuth if you want to test the OAuth path."
    )


def load_frontend_auth(*, redacted: bool = False) -> dict[str, Any]:
    helper = Path(__file__).resolve().parent / "frontend_auth_probe.mjs"
    node = _find_node_runtime()
    if not helper.is_file() or not node:
        return {"ok": False, "error": "Frontend credential probe is not available."}
    command = [node, str(helper)]
    if redacted:
        command.append("--redacted")
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
    except Exception as error:  # noqa: BLE001 - convert probe failure into a UI-friendly diagnostic.
        return {"ok": False, "error": f"Frontend credential probe failed: {error}"}
    payload = (completed.stdout or "").strip().splitlines()[-1:] or [""]
    try:
        data = json.loads(payload[0])
    except json.JSONDecodeError:
        return {"ok": False, "error": (completed.stderr or completed.stdout or "Frontend credential probe returned no JSON.").strip()}
    if completed.returncode != 0 and "error" not in data:
        data["error"] = (completed.stderr or "Frontend credential probe failed.").strip()
    return data


def oauth_rejection_message(original_error: str) -> str:
    return (
        "Frontend OAuth was found, but the OpenAI Audio endpoint rejected it. "
        "Use OPENAI_API_KEY or save an OpenAI API key in the Client Frontend for audio transcription. "
        f"Original error: {original_error}"
    )


def looks_like_auth_failure(message: str) -> bool:
    lowered = message.lower()
    return "401" in lowered or "unauthorized" in lowered or "incorrect api key" in lowered or "invalid" in lowered


def _find_node_runtime() -> str | None:
    machine_root = _find_machine_root()
    candidates = [
        machine_root / "Client Frontend" / "node" / "node.exe",
        Path(shutil.which("node") or ""),
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            return str(candidate)
    return None


def _find_machine_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "Client Frontend").is_dir():
            return candidate
    return Path(__file__).resolve().parent.parent.parent


def _frontend_auth_error(frontend: dict[str, Any], fallback: str) -> str:
    detail = frontend.get("error") or frontend.get("runtime_error") or frontend.get("api_key_error") or frontend.get("token_error")
    if detail:
        return f"{fallback} Frontend credential detail: {detail}"
    return fallback
