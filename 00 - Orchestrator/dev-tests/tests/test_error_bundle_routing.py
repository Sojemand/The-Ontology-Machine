from __future__ import annotations

from pathlib import Path

from orchestrator.models import DocumentRecord, UiState
from orchestrator.pipeline import bundle_repository, policy


def test_error_stage_folder_maps_known_stages() -> None:
    assert policy.error_stage_folder("Intake") == "Intake"
    assert policy.error_stage_folder("Optimizer") == "Optimizer"
    assert policy.error_stage_folder("Request Enrichment") == "Request Enrichment"
    assert policy.error_stage_folder("Interpreter") == "Interpreter"
    assert policy.error_stage_folder("Validator") == "Validator"
    assert policy.error_stage_folder("Normalizer") == "Normalizer"
    assert policy.error_stage_folder("Corpus Builder") == "Corpus Builder"


def test_error_stage_folder_uses_unknown_fallback() -> None:
    assert policy.error_stage_folder("") == "Unbekannt"
    assert policy.error_stage_folder("Unexpected Stage") == "Unbekannt"


def test_bundle_dir_routes_error_bundle_into_stage_subfolder(tmp_path: Path) -> None:
    ui_state = UiState(artifact_folder=str(tmp_path / "artifacts"))
    record = DocumentRecord(
        content_hash="sha256:1234567890abcdef",
        file_name="doc.pdf",
        relative_path="nested/doc.pdf",
        route_family="Documents",
    )

    bundle_dir = bundle_repository.bundle_dir(ui_state, record, stage="Validator", module_name="Validator")

    assert bundle_dir == (
        Path(ui_state.artifact_folder)
        / "Error Cases"
        / "Validator"
        / "Documents"
    )
    assert bundle_dir.is_dir()


def test_bundle_dir_uses_route_family_for_image_errors(tmp_path: Path) -> None:
    ui_state = UiState(artifact_folder=str(tmp_path / "artifacts"))
    record = DocumentRecord(
        content_hash="sha256:fedcba9876543210",
        file_name="scan.jpg",
        relative_path="scan.jpg",
        route_family="Documents",
    )

    bundle_dir = bundle_repository.bundle_dir(ui_state, record, stage="Optimizer", module_name="Optimizer")

    assert bundle_dir == (
        Path(ui_state.artifact_folder)
        / "Error Cases"
        / "Optimizer"
        / "Documents"
    )

