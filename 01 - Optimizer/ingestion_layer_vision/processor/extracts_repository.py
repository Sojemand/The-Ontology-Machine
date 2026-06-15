"""Raw-extract persistence helpers for the processor repository surface."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def write_extract(processor, extract, extracts_dir: Path) -> Path:
    relative_path = extract.source.relative_path or extract.source.filename
    page_suffix = f"_p{extract.page_number:02d}" if extract.page_number is not None else ""
    short_hash = processor._short_output_token(extract.source.content_hash, relative_path)
    slug = processor._build_output_slug(relative_path, extract.source.content_hash)
    payload = _processor_surface().raw_extract_to_dict(extract)
    for output_path in processor._iter_output_candidates(extracts_dir, slug, page_suffix, short_hash):
        if output_path.exists():
            continue
        claim_path = processor._try_claim_output_candidate(output_path)
        if claim_path is None:
            continue
        try:
            if output_path.exists():
                continue
            _processor_surface().atomic_json_write(output_path, payload)
        finally:
            try:
                claim_path.unlink(missing_ok=True)
            except OSError:
                logger.warning("Output-Claim konnte nicht entfernt werden: %s", claim_path)
        return output_path
    raise FileExistsError(f"Kein freier Output-Pfad fuer {relative_path} in {extracts_dir}")


def write_extract_to_path(processor, extract, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _processor_surface().atomic_json_write(output_path, _processor_surface().raw_extract_to_dict(extract))
    return output_path


def build_and_write_extract(processor, **kwargs) -> Path:
    extract = processor._build_extract(**kwargs)
    output_path = processor._write_extract(extract, processor._extracts_dir)
    with processor._report_lock:
        processor._report.total_extracts_written += 1
        processor._report.total_blocks_generated += len(kwargs["blocks"])
        processor._report.total_images_rendered += len(kwargs["image_paths"])
        processor._report.by_format[kwargs["fmt"]] = processor._report.by_format.get(kwargs["fmt"], 0) + 1
        processor._report.by_plugin[kwargs["plugin_name"]] = processor._report.by_plugin.get(kwargs["plugin_name"], 0) + 1
        if kwargs["vision"]:
            processor._report.vision_docs += 1
        else:
            processor._report.text_docs += 1
    return output_path


def _processor_surface():
    return sys.modules[__package__]
