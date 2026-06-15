from __future__ import annotations

from pathlib import Path

import pytest

from validator_vision.main.surface import build_parser
from validator_vision.paths import __all__ as path_exports


MODULE_ROOT = Path(__file__).parent.parent.parent


def test_ui_package_files_are_removed() -> None:
    ui_root = MODULE_ROOT / "validator_vision" / "ui"
    assert not any(ui_root.glob("*.py"))
    assert not any((ui_root / "app").glob("*.py"))


def test_paths_surface_no_longer_exports_ui_state() -> None:
    assert "ui_state_path" not in path_exports


@pytest.mark.parametrize("command", ["show-report", "check-config"])
def test_removed_cli_commands_stay_unavailable(command: str) -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args([command])


def test_validator_stays_free_of_taxonomy_source_and_runtime_bundle_reads() -> None:
    blocked_terms = (
        "taxonomy_sources",
        "runtime_semantic_assets",
        "projection_catalog",
        "build_projection_catalog",
    )
    source_roots = (MODULE_ROOT / "validator_vision",)

    for root in source_roots:
        for path in root.rglob("*.py"):
            content = path.read_text(encoding="utf-8")
            assert not any(term in content for term in blocked_terms), path
