"""Shared mail bundle helpers used by subprocess mail plugins."""
from .common import build_preview_blocks, summarize_manifest
from .outlook_msg import extract_msg_bundle
from .outlook_store import extract_outlook_store_bundle, selftest_outlook_store_backend
from .rfc822 import extract_rfc822_bundle

__all__ = [
    "build_preview_blocks",
    "extract_msg_bundle",
    "extract_outlook_store_bundle",
    "extract_rfc822_bundle",
    "selftest_outlook_store_backend",
    "summarize_manifest",
]
