from __future__ import annotations

import json
from pathlib import Path


def write_debug_bundle(name: str, debug_bundle_dir: Path | None, outcome: dict[str, object]) -> str:
    if debug_bundle_dir is None or "debug_payload" not in outcome:
        return ""
    target = debug_bundle_dir / f"{Path(name).name}.debug.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(outcome["debug_payload"]), encoding="utf-8")
    return str(target)


def write_ocr_request_fixture(ocr_request_dir: Path | None, page_asset_paths: list[str]) -> list[str]:
    if ocr_request_dir is None or not page_asset_paths:
        return []
    target = ocr_request_dir / "ocr.request.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "schema_version": "optimizer_ocr.request.v1",
                "image_inputs": [{"path": path} for path in page_asset_paths],
            }
        ),
        encoding="utf-8",
    )
    return [str(target)]


def write_normalizer_request_fixture(request_output_path: Path | None, structured_path: Path) -> str:
    if request_output_path is None:
        return ""
    request_output_path.parent.mkdir(parents=True, exist_ok=True)
    request_output_path.write_text(
        json.dumps(
            {
                "schema_version": "normalizer.request.v1",
                "structured_path": str(structured_path),
            }
        ),
        encoding="utf-8",
    )
    return str(request_output_path)
