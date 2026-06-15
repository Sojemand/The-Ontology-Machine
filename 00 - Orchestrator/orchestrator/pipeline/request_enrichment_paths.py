"""Path rewriting helpers for interpreter requests."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from .request_enrichment_helpers import relative_path_text, required_list, required_mapping


def rewrite_request_paths(
    request: dict[str, Any],
    *,
    request_parent: Path,
    source_target: Path | None,
    page_targets: tuple[Path, ...],
    page_target_map: dict[Path, Path] | None = None,
    source_request_parent: Path | None = None,
    rewrite_source_file_path: bool = True,
    rewrite_page_asset_paths: bool = True,
) -> dict[str, Any]:
    rewritten = copy.deepcopy(request)
    source = rewritten.get("source")
    if (
        isinstance(source, dict)
        and source_target is not None
        and rewrite_source_file_path
    ):
        source["file_path"] = _rewritten_source_file_path(rewritten, source_target, request_parent)
    page_assets = required_list(rewritten.get("page_assets"), "page_assets")
    if not rewrite_page_asset_paths:
        return rewritten
    selected_page_targets = list(select_request_page_targets(rewritten, page_targets))
    resolved_map = normalized_page_target_map(page_target_map)
    source_asset_parent = request_parent if source_request_parent is None else source_request_parent
    fallback_index = 0
    resolved_targets: list[Path] = []
    for item in page_assets:
        page_asset = required_mapping(item, "page_assets[]")
        mapped_target = mapped_page_target(page_asset, source_asset_parent, resolved_map)
        if mapped_target is not None:
            resolved_targets.append(mapped_target)
            continue
        if fallback_index >= len(selected_page_targets):
            raise ValueError("page_assets do not match the managed page images.")
        resolved_targets.append(selected_page_targets[fallback_index])
        fallback_index += 1
    for item, target in zip(page_assets, resolved_targets):
        page_asset = required_mapping(item, "page_assets[]")
        page_asset["path"] = relative_path_text(target, request_parent)
    return rewritten


def select_request_page_targets(request: dict[str, Any], page_targets: tuple[Path, ...]) -> tuple[Path, ...]:
    if not page_targets:
        return page_targets
    page_assets = required_list(request.get("page_assets", []), "page_assets")
    if len(page_assets) == len(page_targets):
        return page_targets
    if len(page_assets) != 1:
        return page_targets
    context = request.get("context", {}) if isinstance(request.get("context"), dict) else {}
    page_number = context.get("page_number")
    if isinstance(page_number, int) and 1 <= page_number <= len(page_targets):
        return (page_targets[page_number - 1],)
    sheet_number = context.get("sheet_number")
    if isinstance(sheet_number, int) and 1 <= sheet_number <= len(page_targets):
        return (page_targets[sheet_number - 1],)
    return (page_targets[0],)


def normalized_page_target_map(page_target_map: dict[Path, Path] | None) -> dict[Path, Path]:
    normalized: dict[Path, Path] = {}
    for source, target in dict(page_target_map or {}).items():
        normalized[Path(source).expanduser().resolve(strict=False)] = Path(target).expanduser().resolve(strict=False)
    return normalized


def mapped_page_target(
    page_asset: dict[str, Any],
    request_parent: Path,
    page_target_map: dict[Path, Path],
) -> Path | None:
    path_text = str(page_asset.get("path", "")).strip()
    if not path_text:
        return None
    source_path = resolve_request_asset_path(path_text, request_parent)
    return page_target_map.get(source_path)


def resolve_request_asset_path(path_text: str, request_parent: Path) -> Path:
    candidate = Path(path_text).expanduser()
    if not candidate.is_absolute():
        candidate = request_parent / candidate
    return candidate.resolve(strict=False)


def _rewritten_source_file_path(request: dict[str, Any], source_target: Path, request_parent: Path) -> str:
    source = request.get("source") if isinstance(request.get("source"), dict) else {}
    context = request.get("context") if isinstance(request.get("context"), dict) else {}
    base_path = relative_path_text(source_target, request_parent)
    page_suffix = _page_suffix(source.get("file_path")) or _page_suffix(context.get("page_source_path"))
    return f"{base_path}{page_suffix}" if page_suffix else base_path


def _page_suffix(value: Any) -> str:
    text = str(value or "").strip()
    marker_index = text.lower().find("::page=")
    return text[marker_index:] if marker_index >= 0 else ""
