from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileSnapshot:
    path: str
    size: int
    sha256: str


def snapshot_tree(root: Path) -> dict[str, FileSnapshot]:
    if not root.exists():
        return {}
    snapshots: dict[str, FileSnapshot] = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        content = path.read_bytes()
        snapshots[relative] = FileSnapshot(relative, len(content), hashlib.sha256(content).hexdigest())
    return snapshots


def diff_snapshots(before: dict[str, FileSnapshot], after: dict[str, FileSnapshot]) -> dict[str, list[str]]:
    before_keys = set(before)
    after_keys = set(after)
    changed = sorted(key for key in before_keys & after_keys if before[key].sha256 != after[key].sha256)
    return {
        "added": sorted(after_keys - before_keys),
        "removed": sorted(before_keys - after_keys),
        "changed": changed,
    }
