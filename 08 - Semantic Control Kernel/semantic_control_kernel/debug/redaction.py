from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from semantic_control_kernel.repository.paths import path_hash
from semantic_control_kernel.types.debug import REDACTION_PROFILE_IDS
from semantic_control_kernel.validation.debug_validation import validate_redaction_profile
from semantic_control_kernel.debug.redaction_rules import (
    BEARER_RE,
    DATABASE_FIELD_MARKERS,
    OAUTH_TOKEN_RE,
    OPENAI_KEY_RE,
    PROMPT_FIELD_MARKERS,
    RAW_PROVIDER_FIELD_MARKERS,
    SECRET_FIELD_NAMES,
    TRACEBACK_FIELD_MARKERS,
    TRACEBACK_RE,
    UNIX_ABSOLUTE_PATH_RE,
    WINDOWS_ABSOLUTE_PATH_RE,
    contains_secret_field_name,
)
from semantic_control_kernel.debug.redaction_types import RedactionProfile, RedactionStats


class RedactionEngine:
    def __init__(
        self,
        *,
        state_root: str | Path | None = None,
        artifact_roots: Sequence[str | Path] = (),
    ) -> None:
        self.state_root = Path(state_root).resolve(strict=False) if state_root is not None else None
        self.artifact_roots = tuple(Path(root).resolve(strict=False) for root in artifact_roots)

    def profile_payload(self, profile_id: str) -> dict[str, Any]:
        payload = {
            "profile_id": profile_id,
            "raw_payloads_included": False,
            "path_policy": "module_relative_or_hashed",
            "secret_field_names": list(SECRET_FIELD_NAMES),
        }
        validate_redaction_profile(payload)
        return payload

    def redact(self, value: Any, *, profile_id: str) -> tuple[Any, RedactionStats]:
        if profile_id not in REDACTION_PROFILE_IDS:
            raise ValueError(f"Unknown redaction profile: {profile_id}")
        stats = RedactionStats.empty()
        redacted = self._redact_value(value, profile_id=profile_id, stats=stats, key_path="$")
        return redacted, stats

    def safe_summary(self, text: object, *, limit: int = 400) -> str:
        redacted, _ = self.redact(str(text or "Support evidence is available in the Semantic Control Kernel."), profile_id=RedactionProfile.USER_VISIBLE_V1)
        if not isinstance(redacted, str):
            redacted = str(redacted)
        summary = redacted.strip() or "Support evidence is available in the Semantic Control Kernel."
        if len(summary) > limit:
            summary = summary[: limit - 3].rstrip() + "..."
        return summary

    def assert_safe_summary(self, summary: str) -> None:
        if any(pattern.search(summary) for pattern in (OPENAI_KEY_RE, BEARER_RE, OAUTH_TOKEN_RE, WINDOWS_ABSOLUTE_PATH_RE, UNIX_ABSOLUTE_PATH_RE)):
            raise ValueError("safe_summary contains a secret-like token or unredacted absolute path.")
        if TRACEBACK_RE.search(summary):
            raise ValueError("safe_summary contains an unredacted traceback.")

    def build_report(self, *, support_bundle_id: str, profile_id: str, stats: RedactionStats, created_at: str) -> dict[str, Any]:
        return {
            "schema_version": "debug.redaction_report.v1",
            "support_bundle_id": support_bundle_id,
            "redaction_profile": self.profile_payload(profile_id),
            "redacted_field_counts": dict(stats.redacted_field_counts),
            "redacted_path_counts": dict(stats.redacted_path_counts),
            "redacted_secret_counts": dict(stats.redacted_secret_counts),
            "raw_payload_refs_excluded": list(stats.raw_payload_refs_excluded),
            "created_at": created_at,
        }

    def _redact_value(self, value: Any, *, profile_id: str, stats: RedactionStats, key_path: str, parent_key: str = "") -> Any:
        if isinstance(value, Mapping):
            redacted: dict[str, Any] = {}
            for key, child in value.items():
                key_text = str(key)
                lowered = key_text.casefold()
                if contains_secret_field_name(lowered):
                    stats.bump_field(key_text)
                    stats.bump_secret("secret_field_name")
                    redacted[key_text] = "[redacted]"
                    continue
                if any(marker in lowered for marker in PROMPT_FIELD_MARKERS):
                    stats.bump_field(key_text)
                    stats.exclude_raw_ref("prompt_snapshot")
                    redacted[key_text] = "[ref-only:prompt_snapshot]"
                    continue
                if any(marker in lowered for marker in RAW_PROVIDER_FIELD_MARKERS):
                    stats.bump_field(key_text)
                    stats.exclude_raw_ref("raw_provider_output")
                    redacted[key_text] = "[ref-only:raw_provider_output]"
                    continue
                if any(marker in lowered for marker in DATABASE_FIELD_MARKERS):
                    stats.bump_field(key_text)
                    stats.exclude_raw_ref("database_payload")
                    redacted[key_text] = "[ref-only:database_payload]"
                    continue
                if any(marker in lowered for marker in TRACEBACK_FIELD_MARKERS):
                    stats.bump_field(key_text)
                    redacted[key_text] = self._redact_traceback(child, stats)
                    continue
                redacted[key_text] = self._redact_value(
                    child,
                    profile_id=profile_id,
                    stats=stats,
                    key_path=f"{key_path}.{key_text}",
                    parent_key=key_text,
                )
            return redacted
        if isinstance(value, list):
            return [
                self._redact_value(item, profile_id=profile_id, stats=stats, key_path=f"{key_path}[{index}]", parent_key=parent_key)
                for index, item in enumerate(value)
            ]
        if isinstance(value, str):
            return self._redact_string(value, profile_id=profile_id, stats=stats, parent_key=parent_key)
        return value

    def _redact_string(self, value: str, *, profile_id: str, stats: RedactionStats, parent_key: str) -> str:
        if TRACEBACK_RE.search(value):
            return self._redact_traceback(value, stats)
        text = self._redact_secret_and_path_tokens(value, stats)

        if profile_id == RedactionProfile.INTERNAL_REF_ONLY_V1 and parent_key:
            lowered = parent_key.casefold()
            if any(marker in lowered for marker in PROMPT_FIELD_MARKERS):
                stats.exclude_raw_ref("prompt_snapshot")
                return "[ref-only:prompt_snapshot]"
            if any(marker in lowered for marker in RAW_PROVIDER_FIELD_MARKERS):
                stats.exclude_raw_ref("raw_provider_output")
                return "[ref-only:raw_provider_output]"
        return text

    def _redact_traceback(self, value: Any, stats: RedactionStats) -> str:
        stats.bump_secret("traceback")
        text = str(value or "").replace("\\n", "\n")
        detail = "exception recorded"
        for line in reversed(text.splitlines()):
            stripped = line.strip()
            if stripped:
                detail = stripped[:120]
                break
        detail = self._redact_secret_and_path_tokens(detail, stats)
        return f"[redacted traceback] {detail}".strip()

    def _redact_secret_and_path_tokens(self, value: str, stats: RedactionStats) -> str:
        text = value
        if OPENAI_KEY_RE.search(text):
            stats.bump_secret("openai_key")
            text = OPENAI_KEY_RE.sub("[redacted]", text)
        if BEARER_RE.search(text):
            stats.bump_secret("bearer_token")
            text = BEARER_RE.sub("[redacted]", text)
        if OAUTH_TOKEN_RE.search(text):
            stats.bump_secret("oauth_token")
            text = OAUTH_TOKEN_RE.sub("[redacted]", text)
        for match in list(WINDOWS_ABSOLUTE_PATH_RE.finditer(text)):
            text = text.replace(match.group(0), self._path_placeholder(match.group(0), stats))
        for match in list(UNIX_ABSOLUTE_PATH_RE.finditer(text)):
            text = text.replace(match.group(0), self._path_placeholder(match.group(0), stats))
        return text

    def _path_placeholder(self, raw_path: str, stats: RedactionStats) -> str:
        path = Path(raw_path)
        resolved = path.resolve(strict=False)
        if self.state_root is not None:
            try:
                relative = resolved.relative_to(self.state_root)
                return f"state/{relative.as_posix()}"
            except ValueError:
                pass
        for artifact_root in self.artifact_roots:
            try:
                relative = resolved.relative_to(artifact_root)
                return f"artifact:{relative.as_posix()}"
            except ValueError:
                continue
        stats.bump_path("external_absolute")
        ext = resolved.suffix if resolved.suffix else ""
        suffix = f";ext={ext}" if ext else ""
        return f"[path:{path_hash(resolved)};kind=external_absolute{suffix}]"
