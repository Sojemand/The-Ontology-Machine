"""Page-scoped error-case manifest helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models import utc_now_iso
from ..state import atomic_json_write
from . import path_budget, policy, storage_repository


def page_bundle_manifest_path(engine: Any, record: Any, bundle_path: Path, *, page_index: int, page_total: int) -> Path:
    relative_path = policy.error_manifest_output_path(engine, record)
    target_dir = storage_repository.publication_root(bundle_path, "logs") / relative_path.parent
    page_suffix = f".p{page_index + 1:03d}.of{max(page_total, 1):03d}"
    name = relative_path.name
    if name.endswith(".error_manifest.json"):
        name = f"{name[:-len('.error_manifest.json')]}{page_suffix}.error_manifest.json"
    else:
        name = f"{relative_path.stem}{page_suffix}{relative_path.suffix}"
    return target_dir / path_budget.budgeted_name(target_dir, name)


def write_page_bundle_manifest(
    engine: Any,
    record: Any,
    bundle_path: Path,
    *,
    stage: str,
    reason: str,
    disposition: str,
    module_name: str,
    page_index: int,
    page_total: int,
) -> Path:
    payload = record.to_dict()
    payload.update(
        {
            "bundle_module": module_name,
            "bundle_stage": stage,
            "bundle_reason": reason,
            "bundle_disposition": disposition,
            "page_failure": {
                "page_index": page_index,
                "page_number": page_index + 1,
                "page_total": page_total,
            },
            "manifest_updated_at": utc_now_iso(),
        }
    )
    manifest_path = page_bundle_manifest_path(engine, record, bundle_path, page_index=page_index, page_total=page_total)
    atomic_json_write(manifest_path, payload)
    return manifest_path
