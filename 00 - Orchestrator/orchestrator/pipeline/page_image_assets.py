"""Table optimizer page-image helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable


def extra_render_paths_from_raws(raw_path_values: Iterable[str], *, known_path_values: Iterable[str] = ()) -> list[Path]:
    del raw_path_values
    del known_path_values
    return []


__all__ = ["extra_render_paths_from_raws"]
