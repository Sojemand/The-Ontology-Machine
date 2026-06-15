"""Static intake matrix and route helpers for the orchestrator."""

from __future__ import annotations

from pathlib import Path

from .. import policy_store
from . import route_types


def image_suffixes() -> tuple[str, ...]:
    return policy_store.image_suffixes()


def file_suffixes() -> tuple[str, ...]:
    return policy_store.file_suffixes()

def pdf_suffix() -> str:
    return policy_store.pdf_suffix()


def normalized_suffix(path: Path) -> str:
    return path.suffix.strip().lower()


def route_family_for_suffix(suffix: str) -> str:
    if suffix in image_suffixes():
        return route_types.route_family_documents()
    if suffix in file_suffixes() or suffix == pdf_suffix():
        return route_types.route_family_documents()
    return ""


def bundle_route_family(route_family: str) -> str:
    return route_family or policy_store.unrouted_error_family()


def __getattr__(name: str):
    dynamic = {
        "IMAGE_SUFFIXES": image_suffixes,
        "FILE_SUFFIXES": file_suffixes,
        "PDF_SUFFIX": pdf_suffix,
        "UNROUTED_ERROR_FAMILY": policy_store.unrouted_error_family,
    }
    if name in dynamic:
        return dynamic[name]()
    raise AttributeError(name)
