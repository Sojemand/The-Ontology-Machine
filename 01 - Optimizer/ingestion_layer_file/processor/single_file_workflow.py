"""Single-file processor workflow with explicit orchestrator targets."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path

from ..models import BlockPosition, DataBlock, RawExtract
from . import policy, validation, workflow as batch_workflow
from .single_file_build import build_single_extract, single_entry
from .single_file_reporting import record_single_extract


def process_single(
    processor,
    file_path: str | Path,
    write_output: bool = True,
    output_dir: str | Path | None = None,
    *,
    raw_output_path: str | Path | None = None,
    page_assets_dir: str | Path | None = None,
    page_images_dir: str | Path | None = None,
    logical_source_path: str | None = None,
) -> list[RawExtract]:
    source_path = Path(file_path)
    validation.ensure_existing_file(source_path)
    if isinstance(output_dir, dict):  # pragma: no cover - defensive compatibility guard
        raise ValueError("output_dir darf kein Objekt sein.")
    requested_output = Path(output_dir) if output_dir else processor._requested_output_dir
    explicit_raw_output_path = Path(raw_output_path) if raw_output_path else None
    explicit_page_assets_dir = Path(page_assets_dir) if page_assets_dir else (Path(page_images_dir) if page_images_dir else None)
    normalized_logical_path = validation.validate_explicit_single_file_targets(
        write_output=write_output,
        output_dir=requested_output,
        raw_output_path=explicit_raw_output_path,
        page_assets_dir=explicit_page_assets_dir,
        logical_source_path=logical_source_path,
    )
    if normalized_logical_path is None:
        return batch_workflow.process_single(processor, source_path, write_output=write_output, output_dir=requested_output)
    return _process_single_to_explicit_targets(
        processor,
        source_path,
        raw_output_path=explicit_raw_output_path,
        page_images_dir=explicit_page_assets_dir,
        logical_source_path=normalized_logical_path,
    )


def _process_single_to_explicit_targets(
    processor,
    file_path: Path,
    *,
    raw_output_path: Path,
    page_images_dir: Path,
    logical_source_path: str,
) -> list[RawExtract]:
    entry = single_entry(file_path)
    extract = None
    page_extracts: list[RawExtract] = []
    image_paths: list[str] = []
    written_raw: list[Path] = []
    try:
        extract, image_paths = build_single_extract(
            processor,
            entry,
            raw_output_path=raw_output_path,
            page_images_dir=page_images_dir,
            logical_source_path=logical_source_path,
        )
        written_raw.append(processor._write_extract_to_path(extract, raw_output_path))
        page_extracts = _build_page_extracts(extract, logical_source_path)
        for page_extract, page_output_path in zip(page_extracts, _page_raw_output_paths(raw_output_path, len(page_extracts)), strict=False):
            written_raw.append(processor._write_extract_to_path(page_extract, page_output_path))
        record_single_extract(processor, extract, image_count=len(image_paths))
        return [extract, *page_extracts]
    except Exception:
        processor._cleanup_generated_output(
            output_dir=None,
            raw_paths=written_raw,
            image_paths=image_paths,
            asset_dirs=[page_images_dir],
            page_images_root=page_images_dir,
            ingest_id=extract.source.ingest_id if extract is not None else "",
        )
        raise


def _build_page_extracts(extract: RawExtract, logical_source_path: str) -> list[RawExtract]:
    total_pages = len(extract.image_paths)
    if total_pages <= 1:
        page_extract = copy.deepcopy(extract)
        page_extract.page_number = 1
        page_extract.total_pages = 1
        page_extract.image_paths = list(extract.image_paths[:1])
        page_extract.blocks = _blocks_for_page(extract.blocks, 1, 1)
        page_extract.source_blocks = list(page_extract.blocks)
        page_extract.context.page_number = 1
        page_extract.context.document_page_count = 1
        page_extract.context.source_document_path = logical_source_path
        page_extract.context.page_source_path = _page_logical_source_path(logical_source_path, 1, 1)
        _apply_page_source_identity(page_extract)
        return [page_extract]

    page_extracts: list[RawExtract] = []
    for page_number, image_path in enumerate(extract.image_paths, start=1):
        page_extract = copy.deepcopy(extract)
        page_extract.page_number = page_number
        page_extract.total_pages = total_pages
        page_extract.image_paths = [image_path]
        page_extract.blocks = _blocks_for_page(extract.blocks, page_number, total_pages)
        page_extract.source_blocks = list(page_extract.blocks)
        page_extract.context.page_number = page_number
        page_extract.context.document_page_count = total_pages
        page_extract.context.source_document_path = logical_source_path
        page_extract.context.page_source_path = _page_logical_source_path(logical_source_path, page_number, total_pages)
        _apply_page_source_identity(page_extract)
        page_extracts.append(page_extract)
    return page_extracts


def _blocks_for_page(blocks: list[DataBlock], page_number: int, total_pages: int) -> list[DataBlock]:
    filtered: list[DataBlock] = []
    for block in blocks:
        if _block_matches_page(block, page_number, total_pages):
            filtered.append(_clone_block_for_page(block, page_number, total_pages))
    return filtered


def _block_matches_page(block: DataBlock, page_number: int, total_pages: int) -> bool:
    if block.page_span:
        pages = {int(item) for item in block.page_span if item is not None}
        if page_number in pages:
            return True
    block_page = getattr(getattr(block, "position", None), "page", None)
    if block_page is None:
        return total_pages == 1
    return int(block_page) == page_number


def _clone_block_for_page(block: DataBlock, page_number: int, total_pages: int) -> DataBlock:
    cloned = copy.deepcopy(block)
    if cloned.position is None:
        cloned.position = BlockPosition(page=page_number)
    elif cloned.position.page is None and total_pages == 1:
        cloned.position.page = page_number
    return cloned


def _page_raw_output_paths(raw_output_path: Path, total_pages: int) -> list[Path]:
    return policy.page_raw_output_paths(raw_output_path, total_pages)


def _page_logical_source_path(logical_source_path: str, page_number: int, total_pages: int) -> str:
    return f"{logical_source_path}::page={page_number:03d}-of-{total_pages:03d}"


def _apply_page_source_identity(page_extract: RawExtract) -> None:
    page_source_path = str(page_extract.context.page_source_path or "").strip()
    if not page_source_path:
        return
    source = page_extract.source
    source.path = page_source_path
    source.content_hash = _page_content_hash(source.content_hash, page_source_path)


def _page_content_hash(source_hash: str, page_source_path: str) -> str:
    seed = f"{source_hash}|{page_source_path}".encode("utf-8")
    return f"sha256:{hashlib.sha256(seed).hexdigest()}"
