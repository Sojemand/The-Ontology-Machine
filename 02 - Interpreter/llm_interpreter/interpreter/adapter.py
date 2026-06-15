"""Boundary helpers for request loading, batch discovery, and persistence."""
from __future__ import annotations

import copy
import hashlib, re
import json
from pathlib import Path
from typing import Any

from .types import BatchPlanItem, LoadedRequest, RequestInput

_MAX_GENERATED_FILE_NAME_CHARS = 120
_WINDOWS_UNSAFE_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')


def build_loaded_request(
    request: dict[str, Any],
    *,
    label: str | None = None,
    request_path: Path | None = None,
    additional_asset_roots: tuple[Path, ...] = (),
) -> LoadedRequest:
    resolved_request_path = request_path.resolve(strict=False) if request_path is not None else None
    resolved_label = label or _request_label(request, fallback="request.json")
    return LoadedRequest(
        request=request,
        label=resolved_label,
        request_path=resolved_request_path,
        asset_roots=_collect_asset_roots(request, resolved_request_path, additional_asset_roots),
    )


def load_request_payload(request_input: RequestInput) -> LoadedRequest:
    if isinstance(request_input, LoadedRequest):
        return LoadedRequest(
            request=copy.deepcopy(request_input.request),
            label=request_input.label,
            request_path=request_input.request_path,
            asset_roots=request_input.asset_roots,
        )
    if isinstance(request_input, Path):
        payload = json.loads(request_input.read_text(encoding="utf-8"))
        request_path = request_input
        label = request_input.name
    else:
        payload = copy.deepcopy(request_input)
        request_path = None
        label = None
    if not isinstance(payload, dict):
        raise ValueError("Request muss ein JSON-Objekt sein")
    return build_loaded_request(payload, label=label, request_path=request_path)


def write_output(output_path: Path, payload: dict[str, Any], write_json: Any) -> None:
    write_json(output_path, payload)


def default_output_name(request: dict[str, Any], fallback_stem: str = "document") -> str:
    source = request.get("source", {}) or {}
    file_name = str(source.get("file_name", "")).strip()
    if file_name:
        return safe_generated_file_name(Path(file_name).name, ".structured.json", fallback_stem=fallback_stem)
    return safe_generated_file_name(fallback_stem, ".structured.json", fallback_stem="document")


def safe_generated_file_name(label: str, suffix: str, *, fallback_stem: str = "document") -> str:
    stem = _safe_generated_stem(label, fallback_stem=fallback_stem)
    candidate = f"{stem}{suffix}"
    if len(candidate) <= _MAX_GENERATED_FILE_NAME_CHARS:
        return candidate
    digest = hashlib.sha256(stem.encode("utf-8")).hexdigest()[:12]
    budget = _MAX_GENERATED_FILE_NAME_CHARS - len(suffix) - len(digest) - 1
    short_stem = stem[: max(1, budget)].rstrip(" ._-") or fallback_stem
    return f"{short_stem}-{digest}{suffix}"


def _safe_generated_stem(label: str, *, fallback_stem: str) -> str:
    return _WINDOWS_UNSAFE_NAME_CHARS.sub("-", str(label).strip()).strip(" ._-") or fallback_stem


def resolve_batch_output_path(file_path: Path, output_dir: Path) -> Path:
    try:
        loaded_request = load_request_payload(file_path)
    except Exception:
        return output_dir / f"{file_path.stem}.structured.json"
    return output_dir / default_output_name(loaded_request.request, fallback_stem=file_path.stem)


def collect_batch_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    files = [path for path in sorted(input_path.rglob("*.request.json")) if path.is_file()]
    if files:
        return files
    return [
        path
        for path in sorted(input_path.rglob("*.json"))
        if path.is_file()
        if not path.name.endswith(".structured.json")
    ]


def build_batch_error_result(file_path: Path, output_path: Path | None, error: str) -> dict[str, Any]:
    return {
        "status": "error",
        "file": file_path.name,
        "output_path": str(output_path) if output_path is not None else None,
        "error": error,
        "cost_estimate_usd": None,
    }


def plan_batch_outputs(files: list[Path], output_dir: Path) -> list[BatchPlanItem]:
    planned: list[BatchPlanItem] = []
    collisions: dict[str, list[BatchPlanItem]] = {}
    for index, file_path in enumerate(files):
        item = BatchPlanItem(
            index=index,
            file_path=file_path,
            output_path=resolve_batch_output_path(file_path, output_dir),
        )
        planned.append(item)
        collisions.setdefault(_batch_collision_key(item.output_path), []).append(item)
    result: list[BatchPlanItem] = []
    for item in planned:
        colliding = collisions[_batch_collision_key(item.output_path)]
        if len(colliding) == 1:
            result.append(item)
            continue
        names = ", ".join(candidate.file_path.name for candidate in colliding)
        result.append(
            BatchPlanItem(
                index=item.index,
                file_path=item.file_path,
                output_path=item.output_path,
                collision_error=(
                    f"Ausgabekollision: {item.output_path.name} wird von mehreren Requests verwendet "
                    f"({names})"
                ),
            )
        )
    return result


def _batch_collision_key(path: Path) -> str:
    return str(path.resolve(strict=False)).lower()


def _collect_asset_roots(
    request: dict[str, Any],
    request_path: Path | None,
    additional_asset_roots: tuple[Path, ...],
) -> tuple[Path, ...]:
    roots: list[Path] = []
    if request_path is not None:
        roots.append(request_path.parent.resolve(strict=False))
        roots.extend(_request_page_assets_roots(request_path))
    for root in additional_asset_roots:
        roots.append(root.resolve(strict=False))
    source_root = _source_file_root(request, request_path)
    if source_root is not None:
        roots.append(source_root)
    deduped: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if root in seen:
            continue
        seen.add(root)
        deduped.append(root)
    return tuple(deduped)


def _request_label(request: dict[str, Any], *, fallback: str) -> str:
    source = request.get("source", {}) if isinstance(request, dict) else {}
    value = str((source or {}).get("file_name") or "").strip()
    return value or fallback


def _source_file_root(request: dict[str, Any], request_path: Path | None) -> Path | None:
    source = request.get("source", {}) or {}
    if not isinstance(source, dict):
        return None
    source_path_text = str(source.get("file_path", "")).strip()
    if not source_path_text:
        return None
    source_path = Path(source_path_text).expanduser()
    if not source_path.is_absolute() and request_path is not None:
        source_path = request_path.parent / source_path
    return source_path.resolve(strict=False).parent


def _request_page_assets_roots(request_path: Path) -> tuple[Path, ...]:
    for ancestor in request_path.parents:
        if ancestor.name.lower() == "requests":
            root = ancestor.parent
            return (
                (root / "page_assets").resolve(strict=False),
                (root / "artifacts" / "page_assets").resolve(strict=False),
            )
    return ()
