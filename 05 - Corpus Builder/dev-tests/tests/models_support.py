from __future__ import annotations

import os
from pathlib import Path

import pytest


def _link_or_skip(source: Path, link: Path) -> None:
    try:
        os.link(source, link)
    except OSError as exc:
        pytest.skip(f"hardlinks unavailable: {exc}")
