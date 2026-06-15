from __future__ import annotations

import json
from pathlib import Path

from orchestrator.integrations import ClassificationStageResult, ExtractionStageResult, InterpretationStageResult, ValidationStageResult

from .pipeline_document_stage_support import build_raw_payload, optimizer_profile_for_source, sha256
from .pipeline_request_fixture_support import write_debug_bundle, write_ocr_request_fixture


def classify_document(module, source_path: Path) -> ClassificationStageResult:
    outcome = module.next_outcome(source_path.name, "classify", {})
    if outcome:
        if outcome.get("status") == "error":
            return ClassificationStageResult(status="error", error=str(outcome.get("error", "classify failed")))
        return ClassificationStageResult(
            status=str(outcome.get("status", "ok")),
            classification=str(outcome.get("classification", "born_digital_pdf")),
            reason=str(outcome.get("reason", "")),
        )
    if source_path.suffix.lower() != ".pdf":
        return ClassificationStageResult(status="error", error=f"Nicht-PDF fuer classify_document: {source_path}")
    classification = "scan_pdf" if "scan" in source_path.stem.lower() else "born_digital_pdf"
    reason = "Fake scan PDF" if classification == "scan_pdf" else "Fake born-digital PDF"
    return ClassificationStageResult(status="ok", classification=classification, reason=reason)


def extract_document_to_targets(
    module,
    source_path: Path,
    raw_output_path: Path,
    page_images_dir: Path,
    *,
    module_key: str | None = None,
    optimizer_profile: str | None = None,
    logical_source_path: str | None = None,
    runtime_policy_path: Path | None = None,
    ocr_request_dir: Path | None = None,
) -> ExtractionStageResult:
    if hasattr(module, "extract_calls"):
        module.extract_calls.append(
            {
                "module_key": str(module_key or ""),
                "runtime_policy_path": str(runtime_policy_path or ""),
                "logical_source_path": str(logical_source_path or ""),
            }
        )
    effective_source = Path(logical_source_path) if logical_source_path else source_path
    name = effective_source.name
    outcome = module.next_outcome(name, "extract", {"status": "ok"})
    if outcome["status"] != "ok":
        return ExtractionStageResult(error=str(outcome.get("error", "extract failed")))
    content_hash = sha256(source_path)
    raw_path_text = str(outcome["raw_path"]) if "raw_path" in outcome else str(raw_output_path)
    raw_path = Path(raw_path_text) if raw_path_text else None
    page_count, page_path = int(outcome.get("page_count", 1) or 1), Path(str(outcome["page_path"])) if "page_path" in outcome else (page_images_dir / "page_001.jpg")
    raw_doc = {
        "ingest_id": name,
        "path": logical_source_path or str(source_path),
        "file_path": logical_source_path or str(source_path),
        "filename": Path(logical_source_path or str(source_path)).name,
        "file_name": Path(logical_source_path or str(source_path)).name,
        "file_ext": Path(logical_source_path or str(source_path)).suffix.lower(),
        "content_hash": content_hash,
        "page_count": page_count,
    }
    effective_profile = str(optimizer_profile or "").strip().lower()
    if effective_profile not in {"vision", "file"}:
        effective_profile = optimizer_profile_for_source(
            Path(logical_source_path or source_path),
            runtime_policy_path=runtime_policy_path,
        )
    raw_payload = build_raw_payload(effective_profile, raw_doc, page_path)
    if outcome.get("create_raw", True) and raw_path is not None:
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(json.dumps(raw_payload), encoding="utf-8")
    page_raw_paths: list[str] = [raw_path_text] if raw_path_text else []
    page_asset_paths: list[str] = []
    if page_count > 1 and raw_path is not None:
        page_raw_paths = []
        raw_base = raw_path.name[: -len(".raw.json")] if raw_path.name.endswith(".raw.json") else raw_path.stem
        for page_number in range(1, page_count + 1):
            page_raw_path, page_image_path = raw_path.with_name(f"{raw_base}.p{page_number:03d}.of{page_count:03d}.raw.json"), page_images_dir / f"page_{page_number:03d}.jpg"
            page_payload = build_raw_payload(effective_profile, raw_doc, page_image_path, page_number=page_number)
            if outcome.get("create_raw", True):
                page_raw_path.parent.mkdir(parents=True, exist_ok=True)
                page_raw_path.write_text(json.dumps(page_payload), encoding="utf-8")
            if outcome.get("create_page_image", True):
                page_image_path.parent.mkdir(parents=True, exist_ok=True)
                page_image_path.write_text("image", encoding="utf-8")
            page_raw_paths.append(str(page_raw_path))
            page_asset_paths.append(str(page_image_path))
    elif outcome.get("create_page_image", True):
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text("image", encoding="utf-8")
        page_asset_paths.append(str(page_path))
    ocr_request_paths = write_ocr_request_fixture(ocr_request_dir, page_asset_paths)
    return ExtractionStageResult(
        status="ok",
        content_hash=content_hash,
        ingest_id=name,
        document_raw_path=raw_path_text,
        page_raw_paths=page_raw_paths,
        page_asset_paths=page_asset_paths,
        ocr_request_paths=ocr_request_paths,
    )


def interpret_document(
    module,
    input_path: Path,
    output_path: Path,
    *,
    module_key: str | None = None,
    interpreter_profile: str | None = None,
    debug_bundle_dir: Path | None = None,
) -> InterpretationStageResult:
    if hasattr(module, "interpret_calls"):
        module.interpret_calls.append(str(input_path))
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    source = payload.get("source", {}) if isinstance(payload, dict) else {}
    name = str(source.get("file_name", "")).strip() or input_path.name
    source_path = str(source.get("file_path", "")).strip()
    outcome = module.next_outcome(name, "interpret", {"status": "ok"})
    if outcome["status"] == "error":
        return InterpretationStageResult(
            status="error",
            debug_bundle_path=write_debug_bundle(name, debug_bundle_dir, outcome),
            error=str(outcome.get("error", "interpret failed")),
        )
    structured_path = Path(str(outcome.get("structured_path") or output_path))
    context = payload.get("context", {}) if isinstance(payload, dict) else {}
    effective_profile = str(interpreter_profile or "").strip() or str(context.get("interpreter_profile", "")).strip() or "vision"
    structured_payload = {
        "processing": {
            "needs_review": bool(outcome.get("needs_review", False)),
            "review_reason": outcome.get("review_reason", ""),
            "interpreter_profile": effective_profile,
        },
        "classification": {"document_type": "test", "page_count": 1},
        "content": {"free_text": "hello", "fields": {}, "rows": []},
        "source": {
            "file_name": name,
            "file_path": source_path,
            "content_hash": str(source.get("content_hash", "")).strip(),
        },
    }
    if outcome.get("create_structured", True):
        structured_text = outcome.get("structured_text")
        if structured_text is None:
            structured_text = json.dumps(outcome.get("structured_payload", structured_payload))
        structured_path.parent.mkdir(parents=True, exist_ok=True)
        structured_path.write_text(str(structured_text), encoding="utf-8")
    module.structured_to_name[str(structured_path)] = name
    module.structured_name_by_filename[structured_path.name] = name
    return InterpretationStageResult(
        status=str(outcome["status"]),
        structured_path=str(structured_path),
        debug_bundle_path=write_debug_bundle(name, debug_bundle_dir, outcome),
        needs_review=bool(outcome.get("needs_review", False)),
        review_reason=str(outcome.get("review_reason", "")),
    )


def validate_document(
    module,
    structured_path: Path,
    validation_output_path: Path,
    *,
    raw_path: Path | None = None,
) -> ValidationStageResult:
    module.validated_paths.append(str(structured_path))
    module.validator_raw_paths.append(str(raw_path) if raw_path is not None else "")
    name = module.name_for_structured(structured_path)
    outcome = module.next_outcome(name, "validate", {"status": "PASS"})
    if outcome["status"] == "ERROR":
        return ValidationStageResult(status="ERROR", error=str(outcome.get("error", "validate failed")))
    report_path_text = str(outcome["report_path"]) if "report_path" in outcome else str(validation_output_path)
    report_path = Path(report_path_text) if report_path_text else None
    report_payload = {
        "result": outcome["status"],
        "needs_review": bool(outcome.get("needs_review", outcome["status"] in {"WARN", "FAIL"})),
        "summary": {"total_issues": int(outcome.get("issues", 1 if outcome["status"] != "PASS" else 0))},
    }
    if outcome.get("create_report", True) and report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report_payload), encoding="utf-8")
    return ValidationStageResult(
        status=str(outcome["status"]),
        report_path=report_path_text,
        needs_review=bool(report_payload["needs_review"]),
        detail=str(outcome.get("detail", outcome["status"])),
    )

