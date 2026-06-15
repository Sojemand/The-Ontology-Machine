from __future__ import annotations

import os
from pathlib import Path

from orchestrator.pipeline import runtime_retention


def test_run_history_retention_prunes_oldest_unprotected_directories(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runs"
    for index in range(5):
        _run_dir(runtime_root, f"run_{index:02d}", size=8, mtime=1_700_000_000 + index)

    removed = runtime_retention.prune_run_history(
        runtime_root,
        keep_dirs=2,
        max_total_bytes=0,
        protected_names={"run_00"},
    )

    assert [path.name for path in removed] == ["run_01", "run_02", "run_03"]
    assert sorted(path.name for path in runtime_root.iterdir()) == ["run_00", "run_04"]


def test_run_history_retention_prunes_until_total_size_is_bounded(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runs"
    for index in range(4):
        _run_dir(runtime_root, f"run_{index:02d}", size=64, mtime=1_700_000_000 + index)

    runtime_retention.prune_run_history(runtime_root, keep_dirs=10, max_total_bytes=150)

    assert sorted(path.name for path in runtime_root.iterdir()) == ["run_02", "run_03"]


def _run_dir(root: Path, name: str, *, size: int, mtime: int) -> Path:
    path = root / name
    path.mkdir(parents=True, exist_ok=True)
    (path / "run.log").write_bytes(b"x" * size)
    os.utime(path, (mtime, mtime))
    return path
