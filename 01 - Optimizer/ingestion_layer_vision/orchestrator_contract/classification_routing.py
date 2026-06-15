"""Public profile routing for optimizer classification."""
from __future__ import annotations

from ..scan_detector import IMAGE_EXTS
from . import validation

FILE_DOCUMENT_EXTS = {
    ".csv",
    ".doc",
    ".docx",
    ".eml",
    ".emlx",
    ".html",
    ".htm",
    ".json",
    ".log",
    ".markdown",
    ".mbox",
    ".md",
    ".msg",
    ".odt",
    ".oft",
    ".ost",
    ".pst",
    ".rtf",
    ".text",
    ".txt",
    ".xls",
    ".xlsx",
    ".xml",
    ".yaml",
    ".yml",
}


def classify_document(payload: dict, *, pdf_classify) -> dict:
    try:
        source_path = validation.require_source_path(payload)
    except (FileNotFoundError, ValueError) as exc:
        return _error(str(exc))

    suffix = source_path.suffix.lower()
    if suffix in IMAGE_EXTS:
        return _classification(
            classification="image_document",
            optimizer_profile="vision",
            source_kind="image",
            reason=f"image_extension={suffix}; routed_to=vision",
        )
    if suffix == ".pdf":
        return _classify_pdf(payload, pdf_classify=pdf_classify)
    return _classification(
        classification="file_document",
        optimizer_profile="file",
        source_kind="file" if suffix in FILE_DOCUMENT_EXTS else "unknown_file",
        reason=f"extension={suffix or '<none>'}; routed_to=file",
    )


def _classify_pdf(payload: dict, *, pdf_classify) -> dict:
    response = pdf_classify(payload)
    if str(response.get("status", "")).strip().lower() != "ok":
        return response
    classification = str(response.get("classification", "")).strip()
    optimizer_profile = "vision" if classification == "scan_pdf" else "file"
    return {
        **response,
        "optimizer_profile": optimizer_profile,
        "source_kind": "pdf",
        "routing": _routing_payload(optimizer_profile),
    }


def _classification(*, classification: str, optimizer_profile: str, source_kind: str, reason: str) -> dict:
    return {
        "status": "ok",
        "classification": classification,
        "optimizer_profile": optimizer_profile,
        "source_kind": source_kind,
        "reason": reason,
        "routing": _routing_payload(optimizer_profile),
    }


def _routing_payload(optimizer_profile: str) -> dict[str, str]:
    return {
        "contract_module": "ingestion_layer_vision.orchestrator_contract",
        "action": "extract_document",
        "optimizer_profile": optimizer_profile,
    }


def _error(message: str) -> dict:
    return {"status": "error", "error": message}


__all__ = ["FILE_DOCUMENT_EXTS", "classify_document"]
