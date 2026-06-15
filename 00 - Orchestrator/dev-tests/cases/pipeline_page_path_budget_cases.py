from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from orchestrator.models import ArtifactPaths, DocumentRecord
from orchestrator.pipeline import (
    bundle_publication,
    bundle_repository,
    bundle_repository_helpers,
    document_types,
    path_budget,
    policy,
    success_repository_steps,
)


def test_success_named_outputs_rebudget_source_name_under_final_parent(tmp_path: Path) -> None:
    source = _write_text(tmp_path / "working" / f"structured_{'x' * 120}.structured.json", "structured")
    route_root = tmp_path / f"route_{'a' * 48}" / f"branch_{'b' * 48}" / "Documents"
    record = SimpleNamespace(
        relative_path="report.pdf",
        file_name="report.pdf",
        source_path="",
        original_source_path="",
        artifacts=SimpleNamespace(structured_paths=[str(source)], structured_path=""),
    )

    published = success_repository_steps.publish_named_outputs(
        SimpleNamespace(),
        record,
        route_root,
        (tmp_path.resolve(),),
        [],
        attr_list="structured_paths",
        attr_single="structured_path",
        publication_name="structured",
        action="Structured publication",
        noun="Structured-Output",
    )

    assert not isinstance(published, str)
    assert len(published) == 1
    assert len(str(published[0])) <= path_budget.WINDOWS_PATH_BUDGET
    assert published[0].name.endswith(".structured.json")
    assert published[0].read_text(encoding="utf-8") == "structured"


def test_success_page_raw_outputs_rebudget_source_name_under_final_parent(tmp_path: Path) -> None:
    first = _write_text(tmp_path / "working" / f"raw_{'x' * 112}.p001.of002.raw.json", "{}")
    second = _write_text(tmp_path / "working" / f"raw_{'y' * 112}.p002.of002.raw.json", "{}")
    route_root = tmp_path / f"route_{'a' * 48}" / f"branch_{'b' * 48}" / "Documents"
    record = SimpleNamespace(
        relative_path="report.pdf",
        file_name="report.pdf",
        source_path="",
        original_source_path="",
        artifacts=SimpleNamespace(optimizer_raw_paths=[str(first), str(second)]),
    )

    published = success_repository_steps.publish_raw_paths(
        SimpleNamespace(),
        record,
        route_root,
        (tmp_path.resolve(),),
        [],
    )

    assert not isinstance(published, str)
    assert len(published) == 2
    assert all(len(str(path)) <= path_budget.WINDOWS_PATH_BUDGET for path in published)
    assert published[0].name.endswith(".p001.of002.raw.json")
    assert published[1].name.endswith(".p002.of002.raw.json")


def test_error_bundle_named_outputs_rebudget_source_name_under_final_parent(tmp_path: Path) -> None:
    source = _write_text(tmp_path / "working" / f"normalized_{'z' * 110}.structured.normalized.json", "{}")
    target_root = tmp_path / f"bundle_{'a' * 48}" / f"branch_{'b' * 48}" / "normalized"

    copied = bundle_repository_helpers.copy_named_many(
        SimpleNamespace(),
        [str(source)],
        target_root,
        allowed_roots=(tmp_path.resolve(),),
    )

    assert len(copied) == 1
    assert len(str(copied[0])) <= path_budget.WINDOWS_PATH_BUDGET
    assert copied[0].name.endswith(".structured.normalized.json")
    assert copied[0].read_text(encoding="utf-8") == "{}"


def test_error_bundle_raw_target_rebudgets_against_final_parent(tmp_path: Path) -> None:
    source = Path(f"raw_{'q' * 120}.raw.json")
    bundle_path = tmp_path / f"bundle_{'a' * 32}" / f"branch_{'b' * 32}" / "Error Cases" / "Validator"
    record = SimpleNamespace(
        relative_path="report.pdf",
        file_name="report.pdf",
        source_path="",
        original_source_path="",
        artifacts=SimpleNamespace(optimizer_raw_paths=[str(source), "other.raw.json"]),
    )

    target = bundle_repository_helpers.budgeted_raw_target(
        SimpleNamespace(),
        record,
        bundle_path,
        source,
        index=0,
        page_suffix=".p001.of002",
    )

    assert len(str(target)) <= path_budget.WINDOWS_PATH_BUDGET
    assert target.name.endswith(".p001.of002.raw.json")


def test_error_bundle_debug_target_rebudgets_against_final_parent(tmp_path: Path) -> None:
    debug_bundle = Path(f"interpreter_debug_{'d' * 120}.json")
    bundle_path = tmp_path / f"bundle_{'a' * 32}" / f"branch_{'b' * 32}" / "Error Cases" / "Interpreter"
    record = SimpleNamespace(artifacts=SimpleNamespace(interpreter_debug_bundle_path=str(debug_bundle)))

    target = bundle_repository._debug_bundle_target(record, bundle_path, page_suffix=".p001.of002")

    assert len(str(target)) <= path_budget.WINDOWS_PATH_BUDGET
    assert target.parent.name == "p001.of002"
    assert target.name.endswith(".json")


def test_page_stage_paths_keep_distinct_page_suffixes_under_long_names(tmp_path: Path) -> None:
    paths = document_types.DocumentStagePaths(
        doc_runtime_dir=tmp_path / "runtime",
        working_source_path=tmp_path / "source" / "doc.pdf",
        working_artifact_root=tmp_path / "runtime" / "artifacts",
        request_root=tmp_path
        / "runtime"
        / "requests"
        / "BK-20220671 Hin - SKW Piesteritz - GR 2022 - diverse Maschinen - Schmidt Transporte.docx",
        working_request_path=tmp_path / "runtime" / "requests" / "interpreter.request.json",
        interpreter_debug_root=tmp_path / "runtime" / "interpreter_debug",
        working_interpreter_debug_dir=tmp_path / "runtime" / "interpreter_debug",
        structured_root=tmp_path
        / "runtime"
        / "structured"
        / "BK-20220671 Hin - SKW Piesteritz - GR 2022 - diverse Maschinen - Schmidt Transporte.docx",
        working_structured_path=tmp_path / "runtime" / "structured" / "doc.structured.json",
        validation_root=tmp_path
        / "runtime"
        / "validation"
        / "BK-20220671 Hin - SKW Piesteritz - GR 2022 - diverse Maschinen - Schmidt Transporte.docx",
        working_validation_path=tmp_path / "runtime" / "validation" / "doc.files_validation_report.json",
        normalized_root=tmp_path / "runtime" / "normalized",
        working_normalized_path=tmp_path / "runtime" / "normalized" / "doc.structured.normalized.json",
        working_log_path=tmp_path / "runtime" / "logs" / "doc.run.log",
        published_route_root=tmp_path / "artifacts" / "Documents",
        corpus_db_path=tmp_path / "artifacts" / "Corpus" / "corpus.db",
    )
    first = tmp_path / "runtime" / "requests" / "BK-20220671_Hin_-_SKW_Piesteritz_-_GR_2022_-_diverse_Maschinen.0b0a5210.p001.of002" / "interpreter.request.json"
    second = tmp_path / "runtime" / "requests" / "BK-20220671_Hin_-_SKW_Piesteritz_-_GR_2022_-_diverse_Maschinen.0b0a5210.p002.of002" / "interpreter.request.json"

    first_structured = document_types.page_structured_path(paths, first)
    second_structured = document_types.page_structured_path(paths, second)
    first_validation = document_types.page_validation_path(paths, first_structured, files_profile=True)
    second_validation = document_types.page_validation_path(paths, second_structured, files_profile=True)

    assert first_structured != second_structured
    assert first_structured.name.endswith(".p001.of002.structured.json")
    assert second_structured.name.endswith(".p002.of002.structured.json")
    assert first_validation != second_validation
    assert first_validation.name.endswith(".p001.of002.files_validation_report.json")
    assert second_validation.name.endswith(".p002.of002.files_validation_report.json")

def test_page_request_path_keeps_canonical_request_filename_under_long_names(tmp_path: Path) -> None:
    paths = document_types.DocumentStagePaths(
        doc_runtime_dir=tmp_path / "runtime",
        working_source_path=tmp_path / "source" / "doc.pdf",
        working_artifact_root=tmp_path / "runtime" / "artifacts",
        request_root=tmp_path
        / "runtime"
        / "requests"
        / "BK-20220671 Hin - SKW Piesteritz - GR 2022 - diverse Maschinen - Schmidt Transporte.docx",
        working_request_path=tmp_path / "runtime" / "requests" / "interpreter.request.json",
        interpreter_debug_root=tmp_path / "runtime" / "interpreter_debug",
        working_interpreter_debug_dir=tmp_path / "runtime" / "interpreter_debug",
        structured_root=tmp_path / "runtime" / "structured",
        working_structured_path=tmp_path / "runtime" / "structured" / "doc.structured.json",
        validation_root=tmp_path / "runtime" / "validation",
        working_validation_path=tmp_path / "runtime" / "validation" / "doc.files_validation_report.json",
        normalized_root=tmp_path / "runtime" / "normalized",
        working_normalized_path=tmp_path / "runtime" / "normalized" / "doc.structured.normalized.json",
        working_log_path=tmp_path / "runtime" / "logs" / "doc.run.log",
        published_route_root=tmp_path / "artifacts" / "Documents",
        corpus_db_path=tmp_path / "artifacts" / "Corpus" / "corpus.db",
    )
    raw_path = tmp_path / "runtime" / "artifacts" / "raw_extracts" / "BK-20220671_Hin_-_SKW_Piesteritz_-_GR_2022_-_diverse_Maschinen.0b0a5210.p001.of002.raw.json"

    request_path = document_types.page_request_path(paths, raw_path)

    assert request_path.name == policy.request_file_name()
    assert request_path.parent.name.endswith(".p001.of002")

def test_page_stage_paths_use_page_dir_for_budgeted_request_filenames(tmp_path: Path) -> None:
    paths = document_types.DocumentStagePaths(
        doc_runtime_dir=tmp_path / "runtime",
        working_source_path=tmp_path / "source" / "doc.pdf",
        working_artifact_root=tmp_path / "runtime" / "artifacts",
        request_root=tmp_path / "runtime" / "requests",
        working_request_path=tmp_path / "runtime" / "requests" / "interpreter.request.json",
        interpreter_debug_root=tmp_path / "runtime" / "interpreter_debug",
        working_interpreter_debug_dir=tmp_path / "runtime" / "interpreter_debug",
        structured_root=tmp_path / "runtime" / "structured",
        working_structured_path=tmp_path / "runtime" / "structured" / "doc.structured.json",
        validation_root=tmp_path / "runtime" / "validation",
        working_validation_path=tmp_path / "runtime" / "validation" / "doc.files_validation_report.json",
        normalized_root=tmp_path / "runtime" / "normalized",
        working_normalized_path=tmp_path / "runtime" / "normalized" / "doc.structured.normalized.json",
        working_log_path=tmp_path / "runtime" / "logs" / "doc.run.log",
        published_route_root=tmp_path / "artifacts" / "Documents",
        corpus_db_path=tmp_path / "artifacts" / "Corpus" / "corpus.db",
    )
    first = tmp_path / "runtime" / "requests" / "BK-20220671_Hin_-_SKW_Piesteritz_-_G.ef08c2fc.p001.of002" / "interpre.37d5d81d.json"
    second = tmp_path / "runtime" / "requests" / "BK-20220671_Hin_-_SKW_Piesteritz_-_G.a42e9cd2.p002.of002" / "interpre.37d5d81d.json"

    first_structured = document_types.page_structured_path(paths, first)
    second_structured = document_types.page_structured_path(paths, second)
    first_validation = document_types.page_validation_path(paths, first_structured, files_profile=True)
    second_validation = document_types.page_validation_path(paths, second_structured, files_profile=True)
    first_debug_dir = document_types.page_interpreter_debug_dir(paths, first)
    second_debug_dir = document_types.page_interpreter_debug_dir(paths, second)

    assert first_structured != second_structured
    assert first_structured.name.endswith(".p001.of002.structured.json")
    assert second_structured.name.endswith(".p002.of002.structured.json")
    assert first_validation != second_validation
    assert first_validation.name.endswith(".p001.of002.files_validation_report.json")
    assert second_validation.name.endswith(".p002.of002.files_validation_report.json")
    assert first_debug_dir != second_debug_dir
    assert first_debug_dir.name.endswith(".p001.of002")
    assert second_debug_dir.name.endswith(".p002.of002")

def test_copy_requests_to_bundle_budgets_multi_page_request_dirs(tmp_path: Path) -> None:
    first_request_dir = (
        tmp_path
        / "runtime"
        / "requests"
        / "BK-20220671_Hin_-_SKW_Piesteritz_-_GR_2022_-_diverse_Maschinen.0b0a5210.p001.of002"
    )
    second_request_dir = (
        tmp_path
        / "runtime"
        / "requests"
        / "BK-20220671_Hin_-_SKW_Piesteritz_-_GR_2022_-_diverse_Maschinen.0b0a5210.p002.of002"
    )
    first_request_dir.mkdir(parents=True, exist_ok=True)
    second_request_dir.mkdir(parents=True, exist_ok=True)
    first_request_path = first_request_dir / "interpreter.request.json"
    second_request_path = second_request_dir / "interpreter.request.json"
    page_dir = tmp_path / "runtime" / "page_images"
    page_dir.mkdir(parents=True, exist_ok=True)
    first_page_path = page_dir / "page-001.png"
    second_page_path = page_dir / "page-002.png"
    first_page_path.write_text("img", encoding="utf-8")
    second_page_path.write_text("img", encoding="utf-8")
    source_path = tmp_path / "runtime" / "source" / "doc.pdf"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("doc", encoding="utf-8")
    first_request_path.write_text(
        json.dumps(
            {
                "source": {"file_name": "doc.pdf", "file_path": str(source_path)},
                "page_assets": [{"page": 1, "path": str(first_page_path)}],
            }
        ),
        encoding="utf-8",
    )
    second_request_path.write_text(
        json.dumps(
            {
                "source": {"file_name": "doc.pdf", "file_path": str(source_path)},
                "page_assets": [{"page": 2, "path": str(second_page_path)}],
            }
        ),
        encoding="utf-8",
    )
    record = DocumentRecord(
        content_hash="sha256:test",
        file_name="BK-20220671 Hin - SKW Piesteritz - GR 2022 - diverse Maschinen - Schmidt Transporte.docx",
        relative_path="BK-20220671 Hin - SKW Piesteritz - GR 2022 - diverse Maschinen - Schmidt Transporte.docx",
        source_path=str(source_path),
        original_source_path=str(source_path),
        route_family="Documents",
        artifacts=ArtifactPaths(
            interpreter_request_paths=[str(first_request_path), str(second_request_path)]
        ),
    )

    published = bundle_publication.copy_requests_to_bundle(
        SimpleNamespace(),
        record,
        tmp_path
        / "bundle"
        / "Error Cases"
        / "Validator"
        / "Documents",
        allowed_roots=(tmp_path.resolve(),),
        source_path=source_path,
        page_image_paths=(first_page_path, second_page_path),
    )

    assert len(published) == 2
    assert published[0].exists()
    assert published[1].exists()
    assert published[0].parent.name.endswith(".p001.of002")
    assert published[1].parent.name.endswith(".p002.of002")


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
