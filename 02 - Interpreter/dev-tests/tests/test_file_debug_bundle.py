from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from llm_interpreter.interpreter import process_single
from llm_interpreter.models import InterpreterConfig
from llm_interpreter.providers import ProviderError


class _FailingProvider:
    provider_name = "openai"
    _last_usage = {}
    _last_model = "gpt-5.4"

    def generate(self, **_kwargs):
        raise ProviderError("upstream dropped")


def test_file_debug_bundle_records_final_message_snapshot_on_call_provider_failure(sample_request, tmp_path: Path) -> None:
    request = copy.deepcopy(sample_request)
    page_path = tmp_path / "page_assets" / "debug" / "page_001.png"
    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"a" * 20000)
    request["page_assets"] = [{"page": 1, "path": str(page_path), "media_type": "image/png"}]
    request["source"]["page_count"] = 1
    debug_dir = tmp_path / "debug"

    result = process_single(
        request,
        tmp_path / "output" / "scan.pdf.structured.json",
        InterpreterConfig(interpreter_profile="file", max_retries=0, debug_bundle_dir=debug_dir),
        _FailingProvider(),
    )

    payload = json.loads(next(debug_dir.glob("*.debug.json")).read_text(encoding="utf-8"))
    snapshot = payload["message_snapshot"]

    assert result["status"] == "error"
    assert payload["failed_stage"] == "call_provider"
    assert payload["error"] == "upstream dropped"
    assert snapshot["user_block_types"] == ["text", "input_image"]
    assert snapshot["image_block_count"] == 1
