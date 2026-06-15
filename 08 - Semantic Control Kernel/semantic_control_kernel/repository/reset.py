from __future__ import annotations

import shutil
from pathlib import Path

from semantic_control_kernel.repository.atomic_json import AtomicJsonStore
from semantic_control_kernel.repository.errors import KernelStateResetError
from semantic_control_kernel.repository.hard_cap import KernelStateHardCapService
from semantic_control_kernel.repository.ids import generate_id
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.records import ResetManifestRecord


DEFAULT_RESET_ARCHIVE_DIRS: tuple[str, ...] = (
    "workflow_runs/active",
    "resume",
    "pending_confirmations/active",
    "pending_interactions/active",
    "locks/active",
    "events/recovery",
    "events/tool_availability",
    "bindings/records",
    "bindings/index/by_database_path",
    "bindings/index/by_artifact_root",
    "attach_states/by_database",
)

DEFAULT_RESET_PRESERVE_DIRS: tuple[str, ...] = (
    "bindings/history",
    "attach_states/history",
    "receipts",
    "support",
    "events/progress",
    "events/mirror",
    "quarantine",
)


def _validate_reset_manifest(payload: object) -> None:
    if not isinstance(payload, dict):
        raise TypeError("Reset manifest must be an object.")
    ResetManifestRecord.from_dict(payload)


class KernelStateResetService:
    def __init__(self, paths: StatePaths) -> None:
        self.paths = paths
        self._json = AtomicJsonStore(paths, "reset")

    def reset_runtime_state(self, reason: str = "runtime state reset") -> ResetManifestRecord:
        reset_id = generate_id("reset_id")
        reset_root = self.paths.archive_resets_dir / reset_id
        archived_paths: list[str] = []
        try:
            reset_root.mkdir(parents=True, exist_ok=False)
            for relative_dir in DEFAULT_RESET_ARCHIVE_DIRS:
                source_dir = self.paths.safe_path(relative_dir)
                destination_dir = reset_root / relative_dir
                destination_dir.mkdir(parents=True, exist_ok=True)
                if not source_dir.exists():
                    continue
                for child in sorted(source_dir.iterdir()):
                    destination = destination_dir / child.name
                    shutil.move(str(child), str(destination))
                    archived_paths.append(self.paths.relative_to_state_root(source_dir / child.name))
            manifest = ResetManifestRecord(
                {
                    "archived_paths": archived_paths,
                    "created_at": utc_iso(),
                    "preserved_paths": list(DEFAULT_RESET_PRESERVE_DIRS),
                    "reason": reason,
                    "reset_id": reset_id,
                    "schema_version": ResetManifestRecord.SCHEMA_VERSION,
                }
            )
            self._json.write_json(reset_root / "reset_manifest.json", manifest.to_dict(), immutable=True, validator=_validate_reset_manifest)
            for relative_dir in DEFAULT_RESET_ARCHIVE_DIRS:
                self.paths.safe_path(relative_dir).mkdir(parents=True, exist_ok=True)
            KernelStateHardCapService(self.paths).prune_archive_resets()
            return manifest
        except Exception as exc:
            if isinstance(exc, KernelStateResetError):
                raise
            raise KernelStateResetError(str(exc)) from exc
