from __future__ import annotations

import json
from pathlib import Path

from orchestrator.integrations import (
    ClassificationStageResult,
    CorpusLoadStageResult,
    ExtractionStageResult,
    InterpretationStageResult,
    NormalizationStageResult,
    PipelineModules,
    ValidationStageResult,
)
from orchestrator.pipeline import policy as pipeline_policy

from .pipeline_regression_module_support import FixtureReplayModuleSupport
from .pipeline_regression_support import (
    assert_regression_case,
    copy_fixture,
    load_regression_record,
    make_regression_ui_state,
    read_json,
    sha256,
)
from .pipeline_request_fixture_support import write_normalizer_request_fixture, write_ocr_request_fixture

FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "regression"
CASE_NAMES = (
    "happy_path",
    "receipt_live",
    "validator_fail",
    "interpreter_review",
    "normalizer_review",
    "synthetic_scan_pdf_multipage",
    "synthetic_born_digital_pdf_table",
    "synthetic_docx_file_profile",
    "synthetic_msg_thread_file_profile",
    "synthetic_text_file_profile",
    "synthetic_png_vision_profile",
)


class FixtureReplayModules(FixtureReplayModuleSupport, PipelineModules):
    def __init__(self, case_dir: Path, case: dict) -> None:
        self._case_dir = case_dir
        self._stages = case["stages"]
        self._indexes: dict[str, int] = {}
        self.validator_raw_paths: list[str] = []

    def classify_document(self, source_path: Path) -> ClassificationStageResult:
        stage = self._stages.get("classify")
        if isinstance(stage, dict):
            return ClassificationStageResult(
                status=str(stage.get("status", "ok")),
                classification=str(stage.get("classification", "born_digital_pdf")),
                reason=str(stage.get("reason", "")),
            )
        classification = "scan_pdf" if "scan" in source_path.stem.lower() else "born_digital_pdf"
        reason = "Fixture scan PDF" if classification == "scan_pdf" else "Fixture born-digital PDF"
        return ClassificationStageResult(status="ok", classification=classification, reason=reason)

    def extract_document_to_targets(
        self,
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
        del optimizer_profile, runtime_policy_path
        step = self._next("extract")
        name = Path(logical_source_path or source_path).name
        content_hash = sha256(source_path)
        raw_paths = self._copy_raw_fixtures(step, raw_output_path)
        page_paths: list[str] = []
        for index, fixture_name in enumerate(step.get("page_fixtures", []), start=1):
            target = page_images_dir / f"page_{index:03d}{Path(fixture_name).suffix or '.bin'}"
            copy_fixture(self._case_dir / "replay" / fixture_name, target)
            page_paths.append(str(target))
        if module_key == "optimizer" and len(raw_paths) == 1:
            payload = read_json(raw_output_path)
            if "optimizer_profile" not in payload:
                payload["optimizer_profile"] = "file"
            raw_output_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return ExtractionStageResult(
            status=step["status"],
            content_hash=content_hash,
            ingest_id=name,
            document_raw_path=str(raw_output_path),
            page_raw_paths=[str(path) for path in raw_paths],
            page_asset_paths=page_paths,
            ocr_request_paths=write_ocr_request_fixture(ocr_request_dir, page_paths),
        )

    def _copy_raw_fixtures(self, step: dict, raw_output_path: Path) -> list[Path]:
        raw_fixtures = step.get("raw_fixtures")
        if not raw_fixtures:
            copy_fixture(self._case_dir / "replay" / step["raw_fixture"], raw_output_path)
            return [raw_output_path]

        raw_paths: list[Path] = []
        for index, item in enumerate(raw_fixtures):
            fixture_name = str(item["fixture"])
            target = raw_output_path if index == 0 else raw_output_path.with_name(str(item["name"]))
            copy_fixture(self._case_dir / "replay" / fixture_name, target)
            raw_paths.append(target)
        return raw_paths

    def interpret_document(
        self,
        input_path: Path,
        output_path: Path,
        *,
        module_key: str | None = None,
        interpreter_profile: str | None = None,
        debug_bundle_dir: Path | None = None,
    ) -> InterpretationStageResult:
        del debug_bundle_dir, input_path, interpreter_profile, module_key
        step = self._next("interpret")
        copy_fixture(self._case_dir / "replay" / step["structured_fixture"], output_path)
        return InterpretationStageResult(
            status=step["status"],
            structured_path=str(output_path),
            needs_review=bool(step.get("needs_review", False)),
            review_reason=str(step.get("review_reason", "")),
        )

    def validate_document(
        self,
        structured_path: Path,
        validation_output_path: Path,
        *,
        raw_path: Path | None = None,
    ) -> ValidationStageResult:
        step = self._next("validate")
        self.validator_raw_paths.append(str(raw_path) if raw_path is not None else "")
        report_path = validation_output_path
        copy_fixture(self._case_dir / "replay" / step["report_fixture"], report_path)
        return ValidationStageResult(
            status=step["status"],
            report_path=str(report_path),
            needs_review=bool(step.get("needs_review", False)),
            detail=str(step.get("detail", step["status"])),
        )

    def normalize_document(
        self,
        structured_path: Path,
        normalized_output_path: Path,
        *,
        request_output_path: Path | None = None,
        release: dict[str, object] | None = None,
    ) -> NormalizationStageResult:
        del release
        step = self._next("normalize")
        normalized_path = normalized_output_path
        copy_fixture(self._case_dir / "replay" / step["output_fixture"], normalized_path)
        request_path_text = write_normalizer_request_fixture(request_output_path, structured_path)
        return NormalizationStageResult(
            status=step["status"],
            output_path=str(normalized_path),
            request_path=request_path_text,
            needs_review=bool(step.get("needs_review", False)),
            message=str(step.get("message", "")),
            review_reason=str(step.get("review_reason", "")),
        )

    def load_document(
        self,
        structured_path: Path,
        validation_path: Path,
        normalized_path: Path,
        raw_path: Path | None,
        corpus_db_path: Path,
        *,
        persist_page_images_in_db: bool | None = None,
        page_images_dir: Path | None = None,
    ) -> CorpusLoadStageResult:
        del persist_page_images_in_db, page_images_dir
        step = self._next("load")
        if step["status"] in {"loaded", "archived_and_loaded", "skipped"}:
            corpus_db_path.parent.mkdir(parents=True, exist_ok=True)
            corpus_db_path.touch()
        return CorpusLoadStageResult(status=step["status"], reason=str(step.get("reason", "")))
