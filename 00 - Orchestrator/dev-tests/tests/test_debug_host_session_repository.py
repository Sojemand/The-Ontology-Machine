from __future__ import annotations

import os
from pathlib import Path

from orchestrator.debug_host import clear_sessions, has_sessions
from orchestrator.debug_host import session_repository
from orchestrator.debug_host.types import DebugCleanupSummary


def test_clear_sessions_removes_all_debug_session_trees(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    first = _write_session_tree(state_root, "dbg_alpha", "interpreter")
    second = _write_session_tree(state_root, "dbg_beta", "validator")

    summary = clear_sessions(state_root=state_root)

    assert isinstance(summary, DebugCleanupSummary)
    assert summary.removed_sessions == 2
    assert has_sessions(state_root=state_root) is False
    assert not first.exists()
    assert not second.exists()
    assert not (state_root / "debug_sessions").exists()


def test_clear_sessions_is_noop_when_debug_root_is_missing(tmp_path: Path) -> None:
    state_root = tmp_path / "state"

    summary = clear_sessions(state_root=state_root)

    assert summary == DebugCleanupSummary(removed_sessions=0)
    assert has_sessions(state_root=state_root) is False


def test_prune_sessions_bounds_debug_session_history(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    for index in range(5):
        session_root = _write_session_tree(state_root, f"dbg_{index:02d}", "interpreter")
        os.utime(session_root, (1_700_000_000 + index, 1_700_000_000 + index))

    removed = session_repository.prune_sessions(
        state_root=state_root,
        keep_dirs=2,
        max_total_bytes=0,
        protected_session_id="dbg_00",
    )

    assert [path.name for path in removed] == ["dbg_01", "dbg_02", "dbg_03"]
    assert sorted(path.name for path in (state_root / "debug_sessions").iterdir()) == ["dbg_00", "dbg_04"]


def _write_session_tree(state_root: Path, session_id: str, module_key: str) -> Path:
    session_root = state_root / "debug_sessions" / session_id / module_key
    (session_root / "outputs" / "raw_extracts").mkdir(parents=True, exist_ok=True)
    for name in ("request.json", "response.json", "snapshot.json", "result.json", "run.log", "cancel.request"):
        (session_root / name).write_text(name, encoding="utf-8")
    (session_root / "home").mkdir(exist_ok=True)
    (session_root / "outputs" / "raw_extracts" / "invoice.raw.json").write_text("{}", encoding="utf-8")
    return session_root.parent
