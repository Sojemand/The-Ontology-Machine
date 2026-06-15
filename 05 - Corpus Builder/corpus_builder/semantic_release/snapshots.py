"""Path-stable semantic release snapshot API."""

from __future__ import annotations

from .snapshot_identity import (
    build_snapshot_envelope,
    build_snapshot_id,
    recommended_confirmation_filename,
    release_without_active_snapshot,
    resolve_runtime_locale,
)
from .snapshot_storage import (
    count_stale_documents_for_snapshot,
    read_active_snapshot,
    sync_materialization_state_mirrors,
    write_snapshot,
)

__all__ = [
    "build_snapshot_envelope",
    "build_snapshot_id",
    "count_stale_documents_for_snapshot",
    "read_active_snapshot",
    "recommended_confirmation_filename",
    "release_without_active_snapshot",
    "resolve_runtime_locale",
    "sync_materialization_state_mirrors",
    "write_snapshot",
]
