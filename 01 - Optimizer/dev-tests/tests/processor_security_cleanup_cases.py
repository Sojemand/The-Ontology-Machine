from __future__ import annotations

import pytest

from processor_security_env import make_processor


def test_cleanup_rejects_asset_dir_outside_page_assets(tmp_path):
    output_dir = tmp_path / "output"
    page_assets = output_dir / "page_assets"
    page_assets.mkdir(parents=True)

    outside = tmp_path / "outside"
    outside.mkdir()
    marker = outside / "precious.txt"
    marker.write_text("do not delete", encoding="utf-8")

    proc = make_processor(tmp_path)
    proc._cleanup_generated_output(
        output_dir=output_dir,
        raw_paths=[],
        image_paths=[],
        asset_dirs=[outside],
        ingest_id="test-id",
    )

    assert outside.exists(), "Directory outside page_assets must NOT be deleted"
    assert marker.read_text(encoding="utf-8") == "do not delete"


def test_cleanup_rejects_symlinked_asset_dir(tmp_path):
    output_dir = tmp_path / "output"
    page_assets = output_dir / "page_assets"
    page_assets.mkdir(parents=True)

    external = tmp_path / "external"
    external.mkdir()
    (external / "secret.txt").write_text("confidential", encoding="utf-8")

    symlink_dir = page_assets / "legit"
    try:
        symlink_dir.symlink_to(external, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation not supported (requires privileges on Windows)")

    proc = make_processor(tmp_path)
    proc._cleanup_generated_output(
        output_dir=output_dir,
        raw_paths=[],
        image_paths=[],
        asset_dirs=[symlink_dir],
        ingest_id="test-id",
    )

    assert external.exists(), "External target of symlink must NOT be deleted"
    assert (external / "secret.txt").read_text(encoding="utf-8") == "confidential"
