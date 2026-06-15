from __future__ import annotations

from pathlib import Path

MAX_LOC = 200
ROOT = Path(__file__).resolve().parents[2]
SCANNED_ROOTS = (
    ROOT / "mcp_server",
    ROOT / "dev-tests" / "tests",
)
DOCUMENTED_BLUEPRINT_DEBT: set[str] = set()
IGNORED_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "runtime",
    "pytest-cache-files-normalizer",
    "pytest-cache-files-corpus-builder",
    "pytest-cache-files-orchestrator",
}


def test_python_files_stay_within_blueprint_loc_limit() -> None:
    violations: list[str] = []
    for root in SCANNED_ROOTS:
        for path in root.rglob("*.py"):
            if IGNORED_PARTS.intersection(path.parts):
                continue
            line_count = len(path.read_text(encoding="utf-8").splitlines())
            if line_count > MAX_LOC:
                violations.append(path.relative_to(ROOT).as_posix())

    assert sorted(violations) == sorted(DOCUMENTED_BLUEPRINT_DEBT)
