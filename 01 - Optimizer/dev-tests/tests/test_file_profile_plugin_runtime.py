from __future__ import annotations

import sys
from pathlib import Path
import zipfile

import pytest

from ingestion_layer_file import processor as processor_surface
from ingestion_layer_file.models import (
    BlockPosition,
    DataBlock,
    FileFormat,
    IngestionConfig,
    RawExtract,
    RenderPlanResult,
    SourceInfo,
)
from ingestion_layer_file.plugin_manager import PluginManager
from ingestion_layer_file.plugin_manager import adapter
from ingestion_layer_file.processor import single_file_rendering
from ingestion_layer_file.processor.single_file_rendering import render_document_assets
from ingestion_layer_file.processor.single_file_workflow import _build_page_extracts
from ingestion_layer_file.rendering.repository import cleanup_stage_dir, create_stage_dir


def test_file_profile_render_defaults_target_150_dpi_canvas() -> None:
    config = IngestionConfig()

    assert config.render_dpi == 150
    assert config.render_width_px == 1240
    assert config.render_height_px == 1754


def test_file_profile_page_extracts_are_page_scoped() -> None:
    extract = RawExtract(
        source=SourceInfo(
            path="story.odt",
            filename="story.odt",
            relative_path="story.odt",
            content_hash="sha256:" + "a" * 64,
        ),
        image_paths=["page_001.png", "page_002.png"],
        blocks=[
            DataBlock(id="p1", type="paragraph", value="Page 1", position=BlockPosition(page=1)),
            DataBlock(id="p2", type="paragraph", value="Page 2", position=BlockPosition(page=2)),
        ],
    )

    first, second = _build_page_extracts(extract, "queue/story.odt")

    assert first.source.path == "queue/story.odt::page=001-of-002"
    assert second.source.path == "queue/story.odt::page=002-of-002"
    assert first.source.content_hash != extract.source.content_hash
    assert second.source.content_hash != extract.source.content_hash
    assert first.source.content_hash != second.source.content_hash


def test_file_profile_stage_dir_does_not_repeat_long_asset_key(tmp_path: Path) -> None:
    long_key = "201611136_V_-_Reinhard_Feinmechanik_Dietzenbach_-_Bestellung_Tieflochbohrungen"
    dest_dir = tmp_path / "page_assets" / long_key

    stage_dir = create_stage_dir(dest_dir)
    try:
        assert stage_dir.parent == dest_dir.parent
        assert stage_dir.name.startswith(".stage.")
        assert long_key not in stage_dir.name
    finally:
        cleanup_stage_dir(stage_dir)


def test_office_multipage_uses_rendered_blocks_as_page_truth(monkeypatch, tmp_path: Path) -> None:
    native_blocks = [
        DataBlock(id="native_para", type="paragraph", value="Native text without page", position=BlockPosition())
    ]
    rendered_blocks = [
        DataBlock(id="page1_para_0", type="paragraph", value="Rendered page 1", position=BlockPosition(page=1)),
        DataBlock(id="page2_para_0", type="paragraph", value="Rendered page 2", position=BlockPosition(page=2)),
    ]

    def fake_render_non_pdf_document(*_args, **_kwargs):
        return RenderPlanResult(
            blocks=rendered_blocks,
            image_paths=["page_001.png", "page_002.png"],
            render_route="office_to_pdf",
            pagination_source="office_export_pdf",
        )

    monkeypatch.setattr(processor_surface, "render_non_pdf_document", fake_render_non_pdf_document)

    image_paths, blocks, render_route, pagination_source = render_document_assets(
        type("ProcessorStub", (), {"_config": IngestionConfig()})(),
        tmp_path / "story.odt",
        fmt=FileFormat.ODT,
        source_blocks=native_blocks,
        page_images_dir=tmp_path / "page_images",
    )

    assert image_paths == ["page_001.png", "page_002.png"]
    assert [block.id for block in blocks] == ["page1_para_0", "page2_para_0"]
    assert [block.position.page for block in blocks] == [1, 2]
    assert render_route == "office_to_pdf"
    assert pagination_source == "office_export_pdf"


def test_office_single_page_keeps_native_blocks_with_page_one(monkeypatch, tmp_path: Path) -> None:
    native_blocks = [
        DataBlock(id="native_para", type="paragraph", value="Native text without page", position=BlockPosition())
    ]

    def fake_render_non_pdf_document(*_args, **_kwargs):
        return RenderPlanResult(
            blocks=[DataBlock(id="page1_para_0", type="paragraph", value="Rendered page 1", position=BlockPosition(page=1))],
            image_paths=["page_001.png"],
            render_route="office_to_pdf",
            pagination_source="office_export_pdf",
        )

    monkeypatch.setattr(processor_surface, "render_non_pdf_document", fake_render_non_pdf_document)

    _image_paths, blocks, _render_route, _pagination_source = render_document_assets(
        type("ProcessorStub", (), {"_config": IngestionConfig()})(),
        tmp_path / "one_page.odt",
        fmt=FileFormat.ODT,
        source_blocks=native_blocks,
        page_images_dir=tmp_path / "page_images",
    )

    assert [block.id for block in blocks] == ["native_para"]
    assert blocks[0].position.page == 1


def test_text_viewer_multipage_uses_rendered_blocks_as_page_truth(monkeypatch, tmp_path: Path) -> None:
    native_blocks = [
        DataBlock(id="para_1", type="paragraph", value="Native markdown text", position=BlockPosition())
    ]
    rendered_blocks = [
        DataBlock(id="page1_para_0", type="paragraph", value="Rendered page 1", position=BlockPosition(page=1)),
        DataBlock(id="page2_para_0", type="paragraph", value="Rendered page 2", position=BlockPosition(page=2)),
    ]

    def fake_render_non_pdf_document(*_args, **_kwargs):
        return RenderPlanResult(
            blocks=rendered_blocks,
            image_paths=["page_001.png", "page_002.png"],
            render_route="html_viewer_pdf",
            pagination_source="viewer_pdf",
        )

    def fail_page_attribution(*_args, **_kwargs):
        raise AssertionError("text viewer multipage must not use native page attribution")

    monkeypatch.setattr(processor_surface, "render_non_pdf_document", fake_render_non_pdf_document)
    monkeypatch.setattr(single_file_rendering, "apply_page_attribution", fail_page_attribution)

    image_paths, blocks, render_route, pagination_source = render_document_assets(
        type("ProcessorStub", (), {"_config": IngestionConfig()})(),
        tmp_path / "article.md",
        fmt=FileFormat.TEXT,
        source_blocks=native_blocks,
        page_images_dir=tmp_path / "page_images",
    )

    assert image_paths == ["page_001.png", "page_002.png"]
    assert [block.id for block in blocks] == ["page1_para_0", "page2_para_0"]
    assert [block.position.page for block in blocks] == [1, 2]
    assert render_route == "html_viewer_pdf"
    assert pagination_source == "viewer_pdf"


def test_resolve_plugin_python_prefers_bundled_plugin_runtime(tmp_path) -> None:
    mgr = PluginManager(tmp_path / "plugins", IngestionConfig())
    plugin_dir = tmp_path / "plugins" / "mail-outlook-store"
    plugin_dir.mkdir(parents=True)
    runtime_root = plugin_dir / "runtime" / "python"
    runtime_python = runtime_root / ("python.exe" if sys.platform == "win32" else "python")
    runtime_python.parent.mkdir(parents=True, exist_ok=True)
    runtime_python.write_text("", encoding="utf-8")
    (runtime_root / "Lib" / "os.py").parent.mkdir(parents=True, exist_ok=True)
    (runtime_root / "Lib" / "os.py").write_text("", encoding="utf-8")
    (runtime_root / "Lib" / "encodings" / "__init__.py").parent.mkdir(parents=True, exist_ok=True)
    (runtime_root / "Lib" / "encodings" / "__init__.py").write_text("", encoding="utf-8")

    assert mgr._resolve_plugin_python("mail-outlook-store") == runtime_python
    assert mgr._plugin_subprocess_env("mail-outlook-store")["PYTHONHOME"] == str(runtime_root)


def test_resolve_plugin_python_falls_back_to_module_runtime_when_plugin_runtime_is_absent(
    tmp_path,
    monkeypatch,
) -> None:
    mgr = PluginManager(tmp_path / "plugins", IngestionConfig())
    plugin_dir = tmp_path / "plugins" / "mail-outlook-store"
    plugin_dir.mkdir(parents=True)
    monkeypatch.setattr(adapter, "resolve_python", lambda _registry: Path("module-python.exe"))
    monkeypatch.setattr(adapter, "subprocess_env", lambda _registry: {"PYTHONHOME": "module-runtime"})

    assert mgr._resolve_plugin_python("mail-outlook-store") == Path("module-python.exe")
    assert mgr._plugin_subprocess_env("mail-outlook-store") == {"PYTHONHOME": "module-runtime"}


def test_resolve_python_rejects_host_python_fallback(tmp_path) -> None:
    mgr = PluginManager(tmp_path / "plugins", IngestionConfig())
    with pytest.raises(FileNotFoundError, match="gebuendelte Modul-Runtime fehlt"):
        mgr._resolve_python()


def test_selftest_reports_incomplete_plugin_runtime_before_subprocess_launch(tmp_path) -> None:
    mgr = PluginManager(tmp_path / "plugins", IngestionConfig())
    plugin_dir = tmp_path / "plugins" / "mail-outlook-store"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "extractor.py").write_text("print('stub')", encoding="utf-8")
    runtime_root = plugin_dir / "runtime" / "python"
    runtime_python = runtime_root / ("python.exe" if sys.platform == "win32" else "python")
    runtime_python.parent.mkdir(parents=True, exist_ok=True)
    runtime_python.write_text("", encoding="utf-8")

    ok, detail = mgr.selftest("mail-outlook-store")

    assert ok is False
    assert "portable oder embedded Standardbibliothek fehlt" in detail


def test_resolve_plugin_python_accepts_embedded_plugin_runtime(tmp_path) -> None:
    mgr = PluginManager(tmp_path / "plugins", IngestionConfig())
    plugin_dir = tmp_path / "plugins" / "mail-outlook-store"
    plugin_dir.mkdir(parents=True)
    runtime_root = plugin_dir / "runtime" / "python"
    runtime_python = runtime_root / ("python.exe" if sys.platform == "win32" else "python")
    runtime_python.parent.mkdir(parents=True, exist_ok=True)
    runtime_python.write_text("", encoding="utf-8")
    (runtime_root / "python39._pth").write_text("python39.zip\n.\n", encoding="utf-8")
    with zipfile.ZipFile(runtime_root / "python39.zip", "w") as archive:
        archive.writestr("os.pyc", b"stub")
        archive.writestr("encodings/__init__.pyc", b"stub")

    assert mgr._resolve_plugin_python("mail-outlook-store") == runtime_python
    assert mgr._plugin_subprocess_env("mail-outlook-store")["PYTHONHOME"] == str(runtime_root)
