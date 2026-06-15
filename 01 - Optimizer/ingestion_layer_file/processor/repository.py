"""Persistence and output-dir state management for the processor."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import logging
from pathlib import Path
import shutil
import sys
from .domain import BuildExtractRequest

logger = logging.getLogger(__name__)


def _surface_module():
    return sys.modules[__package__]


def write_extract(processor, extract, extracts_dir: Path | None = None) -> Path:
    extracts_dir = Path(extracts_dir or processor._extracts_dir or processor._output_dir / "raw_extracts")
    extracts_dir.mkdir(parents=True, exist_ok=True)
    relative_path = extract.source.relative_path or extract.source.filename
    page_suffix = f"_p{extract.page_number:02d}" if getattr(extract, "page_number", None) is not None else ""
    short_hash = processor._short_output_token(extract.source.content_hash, relative_path)
    slug = processor._build_output_slug(relative_path, extract.source.content_hash)
    try:
        payload = _surface_module().raw_extract_to_dict(extract)
    except ValueError:
        if getattr(extract, "needs_llm_vision", True) or getattr(extract, "image_paths", None):
            raise
        payload = {
            "schema_version": "optimizer_raw_v2",
            "optimizer_profile": "file",
            "source": {},
            "extraction": {},
            "metadata": {},
            "context": {},
            "ocr_reference": {"blocks": []},
        }
    for output_path in processor._iter_output_candidates(extracts_dir, slug, page_suffix, short_hash):
        if output_path.exists():
            continue
        claim_path = processor._try_claim_output_candidate(output_path)
        if claim_path is None:
            continue
        try:
            if output_path.exists():
                continue
            _surface_module().atomic_json_write(output_path, payload)
        finally:
            claim_path.unlink(missing_ok=True)
        return output_path
    raise FileExistsError(f"Kein freier Output-Pfad fuer {relative_path} in {extracts_dir}")


def write_extract_to_path(processor, extract, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _surface_module().atomic_json_write(output_path, _surface_module().raw_extract_to_dict(extract))
    return output_path


def build_and_write_extract(processor, **kwargs) -> Path:
    request = kwargs.pop("request", None) or _build_request_from_kwargs(processor, kwargs)
    extract = kwargs.pop("extract", None) or processor._build_extract(request)
    output_path = processor._write_extract(extract, processor._extracts_dir)
    with processor._report_lock:
        processor._report.total_extracts_written += 1
        processor._report.total_blocks_generated += len(kwargs["blocks"])
        processor._report.total_images_rendered += len(kwargs["image_paths"])
        processor._report.by_format[kwargs["fmt"]] = processor._report.by_format.get(kwargs["fmt"], 0) + 1
        processor._report.by_plugin[kwargs["plugin_name"]] = processor._report.by_plugin.get(kwargs["plugin_name"], 0) + 1
        target = "vision_docs" if kwargs.get("vision", True) else "text_docs"
        setattr(processor._report, target, getattr(processor._report, target) + 1)
    return output_path


def cleanup_generated_output(
    processor,
    *,
    output_dir: Path | None,
    raw_paths: list[Path],
    image_paths: list[str],
    asset_dirs: list[Path] | None = None,
    page_images_root: Path | None = None,
    ingest_id: str,
) -> None:
    for raw_path in raw_paths:
        try:
            raw_path.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("Cleanup fehlgeschlagen fuer Raw-Output %s: %s", raw_path, exc)
    claim_token = processor._claim_token_path(ingest_id, output_dir)
    if claim_token is not None:
        try:
            claim_token.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("Cleanup fehlgeschlagen fuer Claim-Token %s: %s", claim_token, exc)
    if not image_paths and not asset_dirs:
        return
    if page_images_root is None:
        if output_dir is None:
            return
        page_images_root = output_dir / "page_images"
    page_root_resolved = page_images_root.resolve() if page_images_root.exists() else page_images_root
    candidates = list(asset_dirs or []) + [Path(path).parent for path in image_paths if path]
    safe_dirs: set[Path] = set()
    for target in candidates:
        try:
            resolved = target.resolve()
            resolved.relative_to(page_root_resolved)
            safe_dirs.add(resolved)
        except (OSError, ValueError):
            continue
    for target in sorted(safe_dirs, key=lambda path: len(path.parts), reverse=True):
        try:
            shutil.rmtree(target)
        except OSError as exc:
            logger.warning("Cleanup fehlgeschlagen fuer Vision-Assets %s: %s", target, exc)


def cleanup_outputs(processor, raw_paths: list[Path], image_paths: list[str]) -> None:
    cleanup_generated_output(processor, output_dir=processor._output_dir, raw_paths=raw_paths, image_paths=image_paths, asset_dirs=None, ingest_id="")


def write_report(processor) -> None:
    payload = asdict(processor._report)
    payload.pop("current_file", None)
    payload.pop("current_plugin", None)
    _surface_module().atomic_json_write(processor._output_dir / "ingestion_report.json", payload)


def compute_hash(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _build_request_from_kwargs(processor, kwargs: dict) -> BuildExtractRequest:
    entry = kwargs.get("entry")
    if isinstance(entry, dict):
        created = str(entry.get("created", ""))
        modified = str(entry.get("modified", ""))
    else:
        created = str(getattr(entry, "created", ""))
        modified = str(getattr(entry, "modified", ""))
    manifest = processor._plugin_mgr.get_manifest(str(kwargs["plugin_name"]))
    return BuildExtractRequest(
        file_path=Path(kwargs["file_path"]),
        filename=str(kwargs["filename"]),
        relative_path=str(kwargs["relative_path"]),
        size=int(kwargs["size"]),
        fmt=str(kwargs["fmt"]),
        plugin_name=str(kwargs["plugin_name"]),
        plugin_version=manifest.version if manifest else "",
        processing_time_ms=int(kwargs["result"].processing_time_ms),
        plugin_metadata=dict(kwargs["result"].metadata),
        content_hash=str(kwargs["content_hash"]),
        ingest_id=str(kwargs["ingest_id"]),
        source_blocks=list(kwargs["blocks"]),
        image_paths=list(kwargs["image_paths"]),
        page_count=len(kwargs["image_paths"]),
        created=created, modified=modified,
    )
