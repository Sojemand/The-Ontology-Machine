from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from corpus_builder.services import build_load_bundle, load_batch, read_active_semantic_release, semantic_status
from llm_interpreter.interpreter import process_single
from llm_interpreter.models import InterpreterConfig
from normalizer_vision.assets import build_projection_catalog
from normalizer_vision.models import NormalizerRuntimeSettings
from normalizer_vision.normalizer import DocumentNormalizer
from normalizer_vision.runtime_semantic_assets import build_runtime_semantic_assets
from normalizer_vision.semantic_release import build_semantic_release

from step1_contract_context import install_release_payload, make_semantic_context
from step1_contract_normalize import (
    normalize_active_release_payload,
    normalize_normalized_payload,
    normalize_request_payload,
    normalize_semantic_status_payload,
    normalize_structured_payload,
)
from step1_contract_paths import BASELINE, NORMALIZER_ROOT, SAMPLE_DATA
from step1_contract_payloads import build_interpreter_output, build_normalizer_output
from step1_contract_providers import InterpreterMockProvider, NormalizerMockProvider


def live_contract_snapshot_payloads(tmp_path: Path) -> dict[str, Any]:
    request_root = tmp_path / "request_case"
    corpus_root = tmp_path / "corpus_context"
    request_root.mkdir(parents=True, exist_ok=True)

    projection_catalog = build_projection_catalog(NORMALIZER_ROOT).to_dict()
    request_payload = SAMPLE_DATA.build_sample_request(request_root)
    scan_path = request_root / "scan.pdf"
    scan_path.write_bytes(b"%PDF-1.4\n% step1 baseline\n")
    request_payload["source"]["file_path"] = str(scan_path)
    request_payload["projection_catalog"] = projection_catalog
    request_snapshot = normalize_request_payload(request_payload)

    structured_path = request_root / "step1_case.structured.json"
    interpreter_result = process_single(
        request_payload,
        structured_path,
        InterpreterConfig(),
        provider=InterpreterMockProvider(build_interpreter_output()),
    )
    if interpreter_result["status"] not in {"ok", "ok_review"}:
        raise AssertionError(f"Interpreter chain failed: {interpreter_result}")
    structured_payload = json.loads(structured_path.read_text(encoding="utf-8"))
    structured_payload = normalize_structured_payload(structured_payload)
    structured_path.write_text(json.dumps(structured_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    normalized_path = request_root / "step1_case.structured.normalized.json"
    normalizer = DocumentNormalizer.from_project(
        NORMALIZER_ROOT,
        runtime_settings=NormalizerRuntimeSettings(model="gpt-5.4-mini", max_output_tokens=2048),
        provider=NormalizerMockProvider(build_normalizer_output()),
    )
    normalization_result = normalizer.normalize(structured_path, normalized_path)
    if normalization_result.status != "OK":
        raise AssertionError(f"Normalizer chain failed: {normalization_result}")
    normalized_payload = json.loads(normalized_path.read_text(encoding="utf-8"))
    normalized_payload = normalize_normalized_payload(normalized_payload)
    normalized_path.write_text(json.dumps(normalized_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    release_payload = build_semantic_release(NORMALIZER_ROOT)
    runtime_payload = build_runtime_semantic_assets(release_payload).to_dict()

    context = make_semantic_context(corpus_root)
    install_release_payload(context, release_payload)
    validation_path = request_root / "step1_case.vision_validation_report.json"
    validation_path.write_text(
        json.dumps(
            {
                "result": "pass",
                "needs_review": False,
                "summary": {"total_issues": 0},
                "issues": [],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    bundle = build_load_bundle(
        context,
        normalized_path=normalized_path,
        structured_path=structured_path,
        validation_path=validation_path,
    )
    batch_result = load_batch(context, [bundle])
    if batch_result.loaded != 1 or batch_result.errors != 0:
        raise AssertionError(f"Corpus load chain failed: {batch_result}")

    status_payload = normalize_semantic_status_payload(semantic_status(context), context)
    active_release_payload = normalize_active_release_payload(read_active_semantic_release(context), context)

    return {
        BASELINE.REQUEST_SNAPSHOT_NAME: request_snapshot,
        BASELINE.STRUCTURED_SNAPSHOT_NAME: structured_payload,
        BASELINE.NORMALIZED_SNAPSHOT_NAME: normalized_payload,
        BASELINE.PROJECTION_CATALOG_SNAPSHOT_NAME: projection_catalog,
        BASELINE.CONTRACT_RELEASE_SNAPSHOT_NAME: release_payload,
        BASELINE.CONTRACT_RUNTIME_SNAPSHOT_NAME: runtime_payload,
        BASELINE.SEMANTIC_STATUS_SNAPSHOT_NAME: status_payload,
        BASELINE.ACTIVE_RELEASE_SNAPSHOT_NAME: active_release_payload,
    }
