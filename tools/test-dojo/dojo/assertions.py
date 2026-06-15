from __future__ import annotations

from pathlib import Path


class DojoAssertionError(AssertionError):
    """Raised when a Dojo gate fails."""


def assert_within_root(path: Path, root: Path, *, label: str = "path") -> None:
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise DojoAssertionError(f"{label} escapes root: {resolved_path} not under {resolved_root}") from exc
