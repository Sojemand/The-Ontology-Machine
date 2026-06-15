from __future__ import annotations


SUPPORT_BUNDLE_REQUIRED_FILES: tuple[str, ...] = (
    "support_bundle_manifest.json",
    "safe_summary.md",
    "included_refs.json",
    "trace_links.json",
    "redaction_report.json",
)

TRACE_LINK_SNAPSHOT_SCHEMA_VERSION = "debug.trace_link_snapshot.v1"
INCLUDED_REFS_SCHEMA_VERSION = "debug.support_bundle_included_refs.v1"
