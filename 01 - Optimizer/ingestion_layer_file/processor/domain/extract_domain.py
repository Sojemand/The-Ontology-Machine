"""Pure assembly of minimal raw-v2 extracts from typed workflow input."""
from __future__ import annotations

from ...models import ContextInfo, ExtractionInfo, RawExtract, SourceInfo
from .types import BuildExtractRequest

_DOCUMENT_TYPE_KEYS = (
    "document_type",
    "doc_type",
    "estimated_doc_type",
)
_LANGUAGE_KEYS = (
    "language",
    "detected_language",
    "lang",
)


def build_extract(processor, request: BuildExtractRequest) -> RawExtract:
    del processor
    public_relative_path = request.source_relative_path or request.relative_path
    public_path = request.source_path_text or str(request.file_path)
    public_filename = request.source_filename or request.filename
    source = SourceInfo(
        ingest_id=request.ingest_id,
        path=public_path,
        filename=public_filename,
        format=request.fmt,
        file_ext=request.file_path.suffix.lower(),
        document_type=_metadata_string(request.plugin_metadata, _DOCUMENT_TYPE_KEYS),
        language=_metadata_string(request.plugin_metadata, _LANGUAGE_KEYS),
        size_bytes=request.size,
        created=request.created,
        modified=request.modified,
        content_hash=request.content_hash,
        relative_path=public_relative_path,
    )
    context = ContextInfo(
        document_page_count=request.page_count,
        source_document_path=public_path,
        interpreter_profile="file",
    )
    return RawExtract(
        source=source,
        context=context,
        extraction=ExtractionInfo(
            plugin_name=request.plugin_name,
            plugin_version=request.plugin_version,
            processing_time_ms=request.processing_time_ms,
            block_count=len(request.source_blocks),
            ocr_used=False,
        ),
        metadata=dict(request.plugin_metadata),
        needs_llm_vision=True,
        image_paths=list(request.image_paths),
        blocks=list(request.source_blocks),
        source_blocks=list(request.source_blocks),
        total_pages=request.page_count,
    )


def _metadata_string(metadata: dict[str, object], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
