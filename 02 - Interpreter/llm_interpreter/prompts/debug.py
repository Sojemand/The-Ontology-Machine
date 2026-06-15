"""Debug helpers for prompt-visible page assets."""
from __future__ import annotations

from typing import Any

from .types import LoadedPageAsset


def describe_page_assets(
    request: dict[str, Any],
    *,
    page_assets: list[LoadedPageAsset] | None = None,
) -> str:
    pages = page_assets or request.get("page_assets", []) or []
    if not pages:
        return "Keine Seitenbilder vorhanden."
    return "\n".join(
        f"Seite {page.get('page')}: {page.get('path')} [{page.get('media_type') or page.get('format', '?')}]"
        for page in pages
    )


__all__ = ["describe_page_assets"]
