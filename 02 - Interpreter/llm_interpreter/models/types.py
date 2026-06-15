"""Named config types and constants for the interpreter surface."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_MAX_PAGE_ASSETS = 15
DEFAULT_MAX_PAGE_ASSET_BYTES = 12 * 1024 * 1024
DEFAULT_MAX_REQUEST_ASSET_BYTES = 40 * 1024 * 1024
DEFAULT_MAX_WORKERS = 8

VISION_IMAGE_DETAIL = "high"

COST_PER_1K_TOKENS: dict[str, tuple[float, float]] = {
    "gpt-5.2": (0.00175, 0.014),
    "gpt-5": (0.00125, 0.010),
    "gpt-5-mini": (0.00025, 0.002),
    "gpt-4.1": (0.002, 0.008),
    "gpt-4o": (0.0025, 0.010),
}


@dataclass
class InterpreterConfig:
    model: str = "gpt-5.4"
    interpreter_profile: str = "vision"
    api_base_url: str = "https://api.openai.com/v1"
    max_output_tokens: int = 8000
    timeout_seconds: int = 300
    thinking_effort: str = "no thinking"
    max_retries: int = 3
    retry_delay_seconds: int = 5
    debug_bundle_dir: Path | None = None
    max_page_assets: int = DEFAULT_MAX_PAGE_ASSETS
    max_page_asset_bytes: int = DEFAULT_MAX_PAGE_ASSET_BYTES
    max_request_asset_bytes: int = DEFAULT_MAX_REQUEST_ASSET_BYTES
    page_asset_allowed_roots: tuple[Path, ...] = ()
    max_workers: int = DEFAULT_MAX_WORKERS

    def __post_init__(self) -> None:
        if self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens muss positiv sein")
        if self.interpreter_profile not in {"vision", "file"}:
            raise ValueError(f"ungueltiges interpreter_profile: {self.interpreter_profile}")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds muss positiv sein")
        if self.max_retries < 0:
            raise ValueError("max_retries muss >= 0 sein")
        if self.thinking_effort != "no thinking":
            raise ValueError(f"ungueltiges thinking_effort: {self.thinking_effort}")
        if self.max_page_assets <= 0:
            raise ValueError("max_page_assets muss positiv sein")
        if self.max_page_asset_bytes <= 0:
            raise ValueError("max_page_asset_bytes muss positiv sein")
        if self.max_request_asset_bytes <= 0:
            raise ValueError("max_request_asset_bytes muss positiv sein")
        if self.max_workers <= 0:
            raise ValueError("max_workers muss positiv sein")

    @property
    def api_thinking_effort(self) -> str:
        return "none"
