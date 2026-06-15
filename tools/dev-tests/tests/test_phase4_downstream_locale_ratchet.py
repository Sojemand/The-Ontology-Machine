from __future__ import annotations

import json
import sys
from pathlib import Path


PIPELINE_ROOT = Path(__file__).resolve().parents[3]
ORCHESTRATOR_ROOT = PIPELINE_ROOT / "00 - Orchestrator"
OPTIMIZER_ROOT = PIPELINE_ROOT / "01 - Optimizer"
INTERPRETER_ROOT = PIPELINE_ROOT / "02 - Interpreter"

for root in (PIPELINE_ROOT, ORCHESTRATOR_ROOT, OPTIMIZER_ROOT, INTERPRETER_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from orchestrator.integrations.runtime_semantic_assets import build_runtime_semantic_assets
from ingestion_layer_vision.runtime_policy import load_runtime_policy_state
from llm_interpreter.interpreter import _validate_request
from llm_interpreter.models import InterpreterConfig
from llm_interpreter.prompts import build_user_prompt_text
from refresh_phase0_artifacts import project_optimizer_runtime_payload
from tools.phase4_locale_test_support import build_locale_runtime_artifacts


def test_phase4_downstream_locale_bundles_are_consumable_end_to_end(tmp_path: Path) -> None:
    for runtime_locale in ("en",):
        locale_tmp = tmp_path / runtime_locale
        _project_root, release, runtime_payload = build_locale_runtime_artifacts(locale_tmp, runtime_locale=runtime_locale)
        validated_assets = build_runtime_semantic_assets(_StaticModules(runtime_payload), release=release)
        optimizer_runtime_payload = project_optimizer_runtime_payload(runtime_payload)
        runtime_policy_path = locale_tmp / f"runtime_semantic_assets.{runtime_locale}.json"
        runtime_policy_path.write_text(json.dumps(optimizer_runtime_payload), encoding="utf-8")
        state = load_runtime_policy_state(runtime_policy_path)
        request = _sample_request(locale_tmp, projection_catalog=runtime_payload["projection_catalog"], source_language="fr")

        pages = _validate_request(request)
        prompt = build_user_prompt_text(request, InterpreterConfig())

        assert validated_assets["runtime_locale"] == runtime_locale
        assert validated_assets["master_taxonomy_release_id"] == release["master_taxonomy_release_id"]
        assert state.release_fingerprint == runtime_payload["release_fingerprint"]
        assert len(pages) == 2
        assert runtime_payload["projection_catalog"]["release_id"] not in prompt
        assert runtime_payload["projection_catalog"]["release_version"] not in prompt
        assert runtime_payload["projection_catalog"]["release_fingerprint"] not in prompt
        assert runtime_payload["projection_catalog"]["master_taxonomy_release_id"] not in prompt
        assert "runtime_locale" not in prompt


class _StaticModules:
    def __init__(self, runtime_payload: dict[str, object]) -> None:
        self._runtime_payload = runtime_payload

    def build_runtime_semantic_assets(self, release: dict[str, object]) -> dict[str, object]:
        del release
        return {"status": "OK", "runtime_semantic_assets": self._runtime_payload}


def _sample_request(tmp_path: Path, *, projection_catalog: dict[str, object], source_language: str) -> dict[str, object]:
    page_root = tmp_path / "page_assets" / "scan_pdf"
    page_one = _write_page(page_root / "page_001.png", b"\x89PNG\r\n\x1a\npage-001")
    page_two = _write_page(page_root / "page_002.png", b"\x89PNG\r\n\x1a\npage-002")
    return {
        "source": {
            "file_name": "scan.pdf",
            "file_path": str(tmp_path / "scan.pdf"),
            "file_ext": "pdf",
            "content_hash": "sha256:test",
            "page_count": 2,
            "document_type": "invoice",
            "language": source_language,
        },
        "context": {
            "page_number": 1,
            "document_page_count": 2,
            "source_document_path": "scan.pdf",
            "page_source_path": "scan.pdf::page=001-of-002",
        },
        "page_assets": [
            {"page": 1, "path": page_one, "media_type": "image/png"},
            {"page": 2, "path": page_two, "media_type": "image/png"},
        ],
        "ocr_reference": {
            "blocks": [
                {
                    "id": "page1_para_1",
                    "type": "paragraph",
                    "layout_label": "header",
                    "value": "Invoice 2026",
                    "value_type": "text",
                    "position": {"page": 1, "paragraph_index": 0},
                    "confidence": 0.98,
                },
                {
                    "id": "page1_para_2",
                    "type": "paragraph",
                    "value": "Invoice number INV-2026-001",
                    "value_type": "text",
                    "position": {"page": 1, "paragraph_index": 1},
                    "confidence": 0.97,
                },
                {
                    "id": "page2_para_1",
                    "type": "paragraph",
                    "value": "Total 1200.00 EUR",
                    "value_type": "text",
                    "position": {"page": 2, "paragraph_index": 0},
                    "confidence": 0.96,
                },
            ]
        },
        "projection_catalog": projection_catalog,
    }


def _write_page(path: Path, payload: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return str(path)
