"""Config loading and .env parsing for the interpreter surface."""
from __future__ import annotations

import os
from collections.abc import Collection, Mapping, MutableMapping
from pathlib import Path

from .coercion import parse_env_int
from .types import InterpreterConfig

LOCAL_ENV_BLOCKED_KEYS = frozenset(
    {
        "OPENAI_API_KEY",
        "VISION_PROVIDER_ID",
        "VISION_PROVIDER_BASE_URL",
        "VISION_PROVIDER_API_KEY",
        "VISION_PROVIDER_AUTH_MODE",
        "VISION_PROVIDER_OAUTH_ACCESS_TOKEN",
        "VISION_PROVIDER_OAUTH_ACCOUNT_ID",
        "LLM_MODEL",
        "MAX_OUTPUT_TOKENS",
        "THINKING_EFFORT",
    }
)


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        if key:
            values[key] = value
    return values


def load_dotenv_file(
    path: Path,
    *,
    environ: MutableMapping[str, str] | None = None,
    override: bool = False,
    blocked_keys: Collection[str] | None = None,
) -> dict[str, str]:
    target = os.environ if environ is None else environ
    blocked = {str(key) for key in blocked_keys or ()}
    loaded = read_env_file(path)
    applied: dict[str, str] = {}
    for key, value in loaded.items():
        if key in blocked:
            continue
        if override or key not in target:
            target[key] = value
        applied[key] = value
    return applied


def _parse_env_path_list(value: object) -> tuple[Path, ...]:
    if value is None:
        return ()
    seen: set[Path] = set()
    roots: list[Path] = []
    for part in str(value).split(os.pathsep):
        item = part.strip()
        if not item:
            continue
        root = Path(item).expanduser().resolve(strict=False)
        if root in seen:
            continue
        seen.add(root)
        roots.append(root)
    return tuple(roots)


def load_config(environ: Mapping[str, str] | None = None) -> InterpreterConfig:
    """Load non-model runtime config from environment only."""
    env = os.environ if environ is None else environ
    runtime_auth_mode = str(env.get("VISION_PROVIDER_AUTH_MODE", "")).strip().lower()
    debug_bundle_dir = str(env.get("DEBUG_BUNDLE_DIR", "")).strip()
    return InterpreterConfig(
        model="gpt-5.4",
        api_base_url=(
            "https://chatgpt.com/backend-api/codex"
            if runtime_auth_mode == "oauth"
            else (
                env.get("VISION_PROVIDER_BASE_URL")
                or env.get("OPENAI_API_BASE_URL", "https://api.openai.com/v1")
            )
        ),
        max_output_tokens=8000,
        timeout_seconds=parse_env_int(env.get("TIMEOUT_SECONDS"), 300, field="TIMEOUT_SECONDS"),
        thinking_effort="no thinking",
        max_retries=parse_env_int(env.get("MAX_RETRIES"), 3, field="MAX_RETRIES"),
        retry_delay_seconds=parse_env_int(env.get("RETRY_DELAY_SECONDS"), 5, field="RETRY_DELAY_SECONDS"),
        debug_bundle_dir=Path(debug_bundle_dir).expanduser() if debug_bundle_dir else None,
        max_page_assets=parse_env_int(env.get("MAX_PAGE_ASSETS"), 15, field="MAX_PAGE_ASSETS"),
        max_page_asset_bytes=parse_env_int(env.get("MAX_PAGE_ASSET_BYTES"), 12 * 1024 * 1024, field="MAX_PAGE_ASSET_BYTES"),
        max_request_asset_bytes=parse_env_int(env.get("MAX_REQUEST_ASSET_BYTES"), 40 * 1024 * 1024, field="MAX_REQUEST_ASSET_BYTES"),
        page_asset_allowed_roots=_parse_env_path_list(env.get("PAGE_ASSET_ALLOWED_ROOTS")),
        max_workers=parse_env_int(env.get("MAX_WORKERS"), 8, field="MAX_WORKERS"),
    )
