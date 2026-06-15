from __future__ import annotations

import pytest

from ingestion_layer_vision.orchestrator_contract import validation as vision_validation
from ingestion_layer_file.orchestrator_contract import validation as file_validation


@pytest.mark.parametrize("validation", [vision_validation, file_validation])
def test_source_path_must_stay_within_input_root_when_provided(tmp_path, validation) -> None:
    input_root = tmp_path / "input"
    outside_root = tmp_path / "outside"
    input_root.mkdir()
    outside_root.mkdir()
    source = outside_root / "leak.pdf"
    source.write_text("x", encoding="utf-8")

    with pytest.raises(ValueError, match="source_path muss innerhalb von input_root liegen"):
        validation.require_source_path({"source_path": str(source), "input_root": str(input_root)})


@pytest.mark.parametrize("validation", [vision_validation, file_validation])
def test_debug_single_source_path_can_skip_input_root_boundary(tmp_path, validation) -> None:
    input_root = tmp_path / "input"
    outside_root = tmp_path / "outside"
    input_root.mkdir()
    outside_root.mkdir()
    source = outside_root / "sample.pdf"
    source.write_text("x", encoding="utf-8")

    assert validation.require_source_path(
        {"source_path": str(source), "input_root": str(input_root)},
        enforce_input_root=False,
    ) == source


@pytest.mark.parametrize("validation", [vision_validation, file_validation])
def test_output_paths_must_stay_within_output_root_when_provided(tmp_path, validation) -> None:
    output_root = tmp_path / "output"
    outside_root = tmp_path / "outside"
    output_root.mkdir()
    outside_root.mkdir()

    with pytest.raises(ValueError, match="raw_output_path muss innerhalb von output_root liegen"):
        validation.require_raw_output_path(
            {"raw_output_path": str(outside_root / "x.raw.json"), "output_root": str(output_root)}
        )
    if hasattr(validation, "require_page_assets_dir"):
        with pytest.raises(ValueError, match="page_assets_dir muss innerhalb von output_root liegen"):
            validation.require_page_assets_dir(
                {"page_assets_dir": str(outside_root / "pages"), "output_root": str(output_root)}
            )


@pytest.mark.parametrize("validation", [vision_validation, file_validation])
def test_worker_count_is_capped_for_debug_runs(validation) -> None:
    assert validation.require_worker_count({"worker_count": validation.MAX_WORKER_COUNT}) == validation.MAX_WORKER_COUNT
    with pytest.raises(ValueError, match=f"worker_count darf maximal {validation.MAX_WORKER_COUNT} sein"):
        validation.require_worker_count({"worker_count": validation.MAX_WORKER_COUNT + 1})
