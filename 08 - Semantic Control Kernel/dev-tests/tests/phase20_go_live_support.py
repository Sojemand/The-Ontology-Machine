from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


MODULE_ROOT = Path(__file__).resolve().parents[2]
GO_LIVE_ROOT = MODULE_ROOT / "release" / "go_live"

if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from tools.generate_go_live_bundle import phase20_truth_hash  # noqa: E402


def latest_go_live_dir() -> Path:
    candidates = sorted(path for path in GO_LIVE_ROOT.glob("glv_*") if path.is_dir())
    if not candidates:
        pytest.skip("No Phase 20 go-live bundle exists.")
    return candidates[-1]


def load_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    assert isinstance(payload, dict)
    return payload


def command_matrix() -> dict[str, object]:
    return load_json(latest_go_live_dir() / "commands" / "command_matrix.json")
