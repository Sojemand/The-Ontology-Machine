from __future__ import annotations

from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2]
PLUGINS_ROOT = MODULE_ROOT / "plugins"

EXPECTED_PLUGIN_FILES = {
    "docx-python": (
        "extractor.py",
        "plugin.json",
        "requirements.txt",
        "docx_extractor/__init__.py",
        "docx_extractor/adapter.py",
        "docx_extractor/adapter_conversion.py",
        "docx_extractor/ooxml_snapshot.py",
        "docx_extractor/workflow.py",
    ),
    "odt-odfpy": (
        "extractor.py",
        "plugin.json",
        "requirements.txt",
        "odt_extractor/__init__.py",
        "odt_extractor/adapter.py",
        "odt_extractor/workflow.py",
    ),
    "rtf-reader": (
        "extractor.py",
        "plugin.json",
        "requirements.txt",
        "rtf_extractor/__init__.py",
        "rtf_extractor/adapter.py",
        "rtf_extractor/workflow.py",
    ),
    "mail-rfc822": (
        "extractor.py",
        "plugin.json",
    ),
    "mail-outlook-msg": (
        "extractor.py",
        "plugin.json",
    ),
    "mail-outlook-store": (
        "extractor.py",
        "plugin.json",
        "bootstrap.py",
        "requirements.txt",
        "runtime/README.md",
    ),
}


def test_file_profile_plugin_wrappers_ship_required_files() -> None:
    for plugin_name, relative_paths in EXPECTED_PLUGIN_FILES.items():
        plugin_root = PLUGINS_ROOT / plugin_name
        assert plugin_root.is_dir(), plugin_name
        for relative_path in relative_paths:
            assert (plugin_root / relative_path).exists(), f"{plugin_name}: {relative_path}"


def test_mail_plugin_wrappers_import_active_mail_runtime_package() -> None:
    for plugin_name in ("mail-rfc822", "mail-outlook-msg", "mail-outlook-store"):
        wrapper_text = (PLUGINS_ROOT / plugin_name / "extractor.py").read_text(encoding="utf-8")
        assert "ingestion_layer_file.mail_runtime" in wrapper_text
        assert "ingestion_layer_vision.mail_runtime" not in wrapper_text


def test_docx_plugin_default_ocr_root_stays_inside_active_optimizer_module() -> None:
    snapshot_text = (PLUGINS_ROOT / "docx-python" / "docx_extractor" / "ooxml_snapshot.py").read_text(encoding="utf-8")
    assert "optimizer_ocr" in snapshot_text
    assert "extract_page_assets" in snapshot_text
    assert "01 - Image Optimizer" not in snapshot_text


def test_docx_plugin_legacy_doc_conversion_prefers_bundled_libreoffice() -> None:
    conversion_text = (PLUGINS_ROOT / "docx-python" / "docx_extractor" / "adapter_conversion.py").read_text(encoding="utf-8")
    assert "resolve_layout().libreoffice_dir" in conversion_text
    assert "shutil.which" not in conversion_text
    assert "profile_dir.as_uri()" in conversion_text


def test_mail_outlook_store_wrapper_mentions_vendor_runtime_remediation() -> None:
    wrapper_text = (PLUGINS_ROOT / "mail-outlook-store" / "extractor.py").read_text(encoding="utf-8")
    assert 'RUNTIME_VENDOR_DIR = PLUGIN_DIR / "runtime" / "vendor"' in wrapper_text
    assert "pypff/libpff-Paket" in wrapper_text
