from __future__ import annotations

from types import SimpleNamespace

from orchestrator.pipeline import health_profile_policy


def _record(name: str, *, optimizer_module_key: str) -> SimpleNamespace:
    return SimpleNamespace(
        file_name=name,
        source_path=name,
        original_source_path=name,
        optimizer_module_key=optimizer_module_key,
    )


def test_optimizer_required_dependencies_cover_supported_file_routes() -> None:
    records = [
        _record("doc.pdf", optimizer_module_key="optimizer"),
        _record("letter.docx", optimizer_module_key="optimizer"),
        _record("open.odt", optimizer_module_key="optimizer"),
        _record("notes.rtf", optimizer_module_key="optimizer"),
        _record("handover.md", optimizer_module_key="optimizer"),
    ]

    assert health_profile_policy.optimizer_required_dependencies(records) == (
        "pdf-pymupdf",
        "renderer-pdf",
        "docx-python",
        "renderer-office",
        "odt-odfpy",
        "rtf-reader",
        "renderer-html",
    )


def test_build_required_dependencies_by_module_ignores_non_optimizer_routes() -> None:
    records = [
        _record("scan.jpg", optimizer_module_key="optimizer"),
        _record("archive.bin", optimizer_module_key=""),
        _record("config.env", optimizer_module_key="optimizer"),
        _record("second.env", optimizer_module_key="optimizer"),
    ]

    assert health_profile_policy.build_required_dependencies_by_module(records, scope="pipeline_run") == {
        "optimizer": ("optimizer_ocr", "renderer-html"),
    }
    assert health_profile_policy.build_required_dependencies_by_module(records, scope="manual_check") == {}


def test_optimizer_required_dependencies_uses_abstract_ocr_fallback_for_vision_routes() -> None:
    records = [
        _record("scan.jpg", optimizer_module_key="optimizer"),
        _record("diagram.png", optimizer_module_key="optimizer"),
    ]

    assert health_profile_policy.optimizer_required_dependencies(records) == ("optimizer_ocr",)

