from __future__ import annotations

from pathlib import Path

from ..artifacts import diff_snapshots, snapshot_tree


def diff_tree(root: Path, callback) -> dict[str, list[str]]:
    before = snapshot_tree(root)
    callback()
    after = snapshot_tree(root)
    return diff_snapshots(before, after)
