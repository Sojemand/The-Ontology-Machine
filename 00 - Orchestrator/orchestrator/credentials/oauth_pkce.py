"""PKCE helpers for browser-based Orchestrator OAuth login."""

from __future__ import annotations

import base64
import hashlib
import secrets


def generate_code_verifier(length: int = 64) -> str:
    if length < 43:
        raise ValueError("PKCE verifier length must be >= 43")
    raw = secrets.token_urlsafe(length)
    return raw[: max(length, 43)]


def build_code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def generate_state() -> str:
    return secrets.token_urlsafe(24)
