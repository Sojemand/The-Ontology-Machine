from __future__ import annotations

import json
from pathlib import Path

import pytest

from llm_interpreter.interpreter import process_single
from llm_interpreter.models import InterpreterConfig
from tests.support.provider_stubs import MockProvider

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "golden"
_PNG_BYTES = b"\x89PNG\r\n\x1a\nGOLDEN"


@pytest.mark.parametrize(
    ("name", "profile"),
    [
        ("vision_scan", "vision"),
        ("file_born_digital", "file"),
    ],
)
def test_golden_path_persisted_output_matches_fixture(tmp_path: Path, name: str, profile: str) -> None:
    request = _load_json(FIXTURE_ROOT / f"{name}.request.json")
    provider_payload = _load_json(FIXTURE_ROOT / f"{name}.provider.json")
    expected = _load_json(FIXTURE_ROOT / f"{name}.expected.structured.json")
    page_path = tmp_path / "page_001.png"
    page_path.write_bytes(_PNG_BYTES)
    request["page_assets"][0]["path"] = str(page_path)
    output_path = tmp_path / f"{name}.structured.json"

    result = process_single(
        request,
        output_path,
        InterpreterConfig(interpreter_profile=profile, page_asset_allowed_roots=(tmp_path,)),
        MockProvider(response_json=provider_payload),
    )
    actual = _load_json(output_path)
    actual["processing"].pop("processed_at", None)

    assert result["status"] == "ok"
    assert actual == expected


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
