"""Single-file processor workflow."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path

from ..models import RawExtract
from . import adapter, validation
from . import policy as processor_policy
from .source_workflow import _extract_source, _prepare_source
from .types import OutputArtifacts


def process_single(
    processor,
    file_path: str | Path,
    write_output: bool = True,
    output_dir: str | Path | None = None,
    *,
    raw_output_path: str | Path | None = None,
    page_assets_dir: str | Path | None = None,
    logical_source_path: str | None = None,
):
    source_path = Path(file_path)
    validation.ensure_existing_file(source_path)
    source = _prepare_source(processor, adapter.build_single_entry(source_path, ""))
    if isinstance(output_dir, dict):  # pragma: no cover - defensive compatibility guard
        raise ValueError("output_dir darf kein Objekt sein.")
    requested_output = Path(output_dir) if output_dir else processor._requested_output_dir
    explicit_raw_output_path = Path(raw_output_path) if raw_output_path else None
    explicit_page_assets_dir = Path(page_assets_dir) if page_assets_dir else None
    normalized_logical_path = validation.validate_explicit_single_file_targets(
        write_output=write_output,
        output_dir=requested_output,
        raw_output_path=explicit_raw_output_path,
        page_assets_dir=explicit_page_assets_dir,
        logical_source_path=logical_source_path,
    )
    explicit_targets_requested = normalized_logical_path is not None
    if not explicit_targets_requested and write_output and requested_output is None:
        raise ValueError("process_single() mit write_output=True erfordert ein output_dir")

    effective_output = None
    if write_output and requested_output and not explicit_targets_requested:
        effective_output = processor._prepare_output_dir(requested_output)

    artifacts = OutputArtifacts()
    page_extracts: list[RawExtract] = []
    try:
        _extract_source(processor, source)
        if source.vision:
            if explicit_page_assets_dir is not None:
                artifacts.asset_dirs.append(explicit_page_assets_dir)
                artifacts.image_paths = processor._render_vision_assets(
                    source.file_path,
                    page_assets_dir=explicit_page_assets_dir,
                    render_config=source.render_config,
                )
            else:
                effective_output = processor._require_vision_output_dir(source.file_path, effective_output)
                asset_key = processor._build_asset_key(source.filename, source.content_hash)
                artifacts.asset_dirs.append(effective_output / "page_assets" / asset_key)
                artifacts.image_paths = processor._render_vision_assets(
                    source.file_path,
                    effective_output,
                    asset_key,
                    render_config=source.render_config,
                )

        source.result, source.plugin_name, source.ocr_was_used = processor._apply_ocr_route(
            file_path=source.file_path,
            filename=source.filename,
            ext=source.ext,
            plugin_name=source.plugin_name,
            result=source.result,
            scan_detected=source.scan_detected,
            vision=source.vision,
            image_paths=artifacts.image_paths,
            requires_ocr=source.ocr_required,
            wants_backup_ocr=source.backup_ocr_requested,
        )
        artifacts.blocks = processor._parse_blocks(source.result.blocks)
        public_relative_path = normalized_logical_path or source.relative_path
        extract = processor._build_extract(
            entry=source.entry,
            file_path=source.file_path,
            filename=source.filename,
            ext=source.ext,
            fmt=source.fmt,
            relative_path=source.relative_path,
            size=source.size,
            result=source.result,
            plugin_name=source.plugin_name,
            blocks=artifacts.blocks,
            vision=source.vision,
            scan_detected=source.scan_detected,
            ocr_was_used=source.ocr_was_used,
            image_paths=artifacts.image_paths,
            content_hash=source.content_hash,
            ingest_id=source.ingest_id,
            source_path_text=normalized_logical_path,
            source_filename=Path(public_relative_path).name,
            source_relative_path=public_relative_path,
        )
        if write_output:
            if explicit_raw_output_path is not None:
                artifacts.written_extract_paths.append(
                    processor._write_extract_to_path(extract, explicit_raw_output_path)
                )
                page_extracts = _build_page_extracts(extract, normalized_logical_path or public_relative_path)
                for page_extract, page_output_path in zip(
                    page_extracts,
                    _page_raw_output_paths(explicit_raw_output_path, len(page_extracts)),
                    strict=False,
                ):
                    artifacts.written_extract_paths.append(
                        processor._write_extract_to_path(page_extract, page_output_path)
                    )
            elif effective_output is not None:
                extracts_dir = effective_output / "raw_extracts"
                extracts_dir.mkdir(parents=True, exist_ok=True)
                artifacts.written_extract_paths.append(processor._write_extract(extract, extracts_dir))
        return [extract, *page_extracts] if explicit_targets_requested else [extract]
    except Exception:
        if write_output:
            processor._cleanup_generated_output(
                output_dir=effective_output,
                raw_paths=artifacts.written_extract_paths,
                image_paths=artifacts.image_paths,
                asset_dirs=artifacts.asset_dirs,
                page_assets_root=explicit_page_assets_dir,
                ingest_id=source.ingest_id,
            )
        raise
    finally:
        if write_output and effective_output is not None:
            processor._release_output_claim()


def _build_page_extracts(extract: RawExtract, logical_source_path: str) -> list[RawExtract]:
    total_pages = len(extract.image_paths)
    if total_pages <= 1:
        page_extract = copy.deepcopy(extract)
        page_extract.page_number = 1
        page_extract.total_pages = 1
        page_extract.source.path = _page_logical_source_path(logical_source_path, 1, 1)
        page_extract.source.relative_path = page_extract.source.path
        page_extract.source.content_hash = _page_content_hash(page_extract.source.content_hash, page_extract.source.path)
        page_extract.image_paths = list(extract.image_paths[:1])
        page_extract.blocks = list(extract.blocks)
        return [page_extract]

    page_extracts: list[RawExtract] = []
    for page_number, image_path in enumerate(extract.image_paths, start=1):
        page_extract = copy.deepcopy(extract)
        page_extract.page_number = page_number
        page_extract.total_pages = total_pages
        page_extract.source.path = _page_logical_source_path(logical_source_path, page_number, total_pages)
        page_extract.source.relative_path = page_extract.source.path
        page_extract.source.content_hash = _page_content_hash(page_extract.source.content_hash, page_extract.source.path)
        page_extract.image_paths = [image_path]
        page_blocks = [block for block in extract.blocks if int(block.position.page or 1) == page_number]
        page_extract.blocks = page_blocks
        page_extracts.append(page_extract)
    return page_extracts


def _page_raw_output_paths(raw_output_path: Path, total_pages: int) -> list[Path]:
    return processor_policy.page_raw_output_paths(raw_output_path, total_pages)


def _page_logical_source_path(logical_source_path: str, page_number: int, total_pages: int) -> str:
    return f"{logical_source_path}::page={page_number:03d}-of-{total_pages:03d}"


def _page_content_hash(source_hash: str, page_source_path: str) -> str:
    seed = f"{source_hash}|{page_source_path}".encode("utf-8")
    return f"sha256:{hashlib.sha256(seed).hexdigest()}"
