from __future__ import annotations

import re

SECRET_FIELD_NAMES: tuple[str, ...] = (
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "client_secret",
    "cookie",
    "credential",
    "oauth",
    "password",
    "refresh_token",
    "secret",
    "session",
    "token",
    "vault",
)

PROMPT_FIELD_MARKERS: tuple[str, ...] = ("prompt", "messages", "bindings")
RAW_PROVIDER_FIELD_MARKERS: tuple[str, ...] = ("raw_provider_response", "output_text")
DATABASE_FIELD_MARKERS: tuple[str, ...] = (
    "normalized_json",
    "structured_json",
    "document_payloads",
    "embeddings",
    "document_text",
    "extracted_page_text",
)
TRACEBACK_FIELD_MARKERS: tuple[str, ...] = ("traceback", "stack_trace", "stacktrace")

OPENAI_KEY_RE = re.compile(r"\bsk-[A-Za-z0-9_\-]{8,}\b")
BEARER_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._\-]+\b", re.IGNORECASE)
OAUTH_TOKEN_RE = re.compile(r"\b(?:ya29|gho|ghp|xox[pbar]-)[A-Za-z0-9._\-]+\b")
WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"(?i)\b[A-Z]:\\[^:*?\"<>|\r\n]+")
UNIX_ABSOLUTE_PATH_RE = re.compile(r"(?<![A-Za-z0-9_./-])/(?:[^/\s]+/)+[^/\s]*")
TRACEBACK_RE = re.compile(r"Traceback \(most recent call last\):", re.IGNORECASE)


def contains_secret_field_name(lowered: str) -> bool:
    return any(fragment in lowered for fragment in SECRET_FIELD_NAMES)
