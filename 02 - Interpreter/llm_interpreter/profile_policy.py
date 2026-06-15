"""Shared interpreter-profile policy for the merged runtime."""
from __future__ import annotations

from typing import Any

DEFAULT_INTERPRETER_PROFILE = "vision"
INTERPRETER_PROFILES = frozenset({"vision", "file"})
_REQUEST_PROFILE_KEY = "_interpreter_profile"


def normalize_profile(value: Any, *, default: str = DEFAULT_INTERPRETER_PROFILE) -> str:
    profile = str(value or "").strip().lower()
    return profile if profile in INTERPRETER_PROFILES else default


def payload_profile(payload: dict[str, Any]) -> str:
    return normalize_profile(payload.get("interpreter_profile"))


def request_profile(request: dict[str, Any]) -> str:
    profile = normalize_profile(request.get(_REQUEST_PROFILE_KEY), default="")
    if profile:
        return profile
    context = request.get("context")
    if isinstance(context, dict):
        profile = normalize_profile(context.get("interpreter_profile"), default="")
        if profile:
            return profile
    return normalize_profile(request.get("interpreter_profile"))


def request_has_explicit_profile(request: dict[str, Any]) -> bool:
    if normalize_profile(request.get(_REQUEST_PROFILE_KEY), default=""):
        return True
    if normalize_profile(request.get("interpreter_profile"), default=""):
        return True
    context = request.get("context")
    return isinstance(context, dict) and bool(normalize_profile(context.get("interpreter_profile"), default=""))


def attach_profile(request: dict[str, Any], profile: str) -> None:
    request[_REQUEST_PROFILE_KEY] = normalize_profile(profile)


__all__ = [
    "DEFAULT_INTERPRETER_PROFILE",
    "INTERPRETER_PROFILES",
    "attach_profile",
    "normalize_profile",
    "payload_profile",
    "request_has_explicit_profile",
    "request_profile",
]
