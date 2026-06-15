from __future__ import annotations

from pathlib import Path

import pytest

from semantic_control_kernel.repository.atomic_json import AtomicJsonStore
from semantic_control_kernel.repository.errors import StateCorruptionError
from semantic_control_kernel.repository.paths import StatePaths


def test_corrupt_json_is_quarantined_with_reason_sidecar(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    store = AtomicJsonStore(paths, "workflow_runs")
    corrupt = paths.safe_path("workflow_runs", "active", "corrupt.json")
    corrupt.write_text("{not json", encoding="utf-8")

    with pytest.raises(StateCorruptionError):
        store.read_json(corrupt)

    quarantine_dir = paths.quarantine_corrupt_dir / "workflow_runs"
    quarantined = [path for path in quarantine_dir.iterdir() if path.name.endswith("corrupt.json")]
    reasons = [path for path in quarantine_dir.iterdir() if path.name.endswith(".reason.json")]

    assert not corrupt.exists()
    assert len(quarantined) == 1
    assert len(reasons) == 1
    assert "corrupt.json" in reasons[0].read_text(encoding="utf-8")
