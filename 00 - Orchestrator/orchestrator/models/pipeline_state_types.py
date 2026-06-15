"""Pipeline state types for orchestrator records and persisted artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .coercion import coerce_bool, coerce_int, coerce_str, coerce_str_list


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ArtifactPaths:
    optimizer_raw_paths: list[str] = field(default_factory=list)
    optimizer_page_image_paths: list[str] = field(default_factory=list)
    optimizer_ocr_request_paths: list[str] = field(default_factory=list)
    optimizer_ocr_request_path: str = ""
    interpreter_request_paths: list[str] = field(default_factory=list)
    interpreter_request_path: str = ""
    interpreter_debug_bundle_path: str = ""
    structured_paths: list[str] = field(default_factory=list)
    structured_path: str = ""
    normalized_paths: list[str] = field(default_factory=list)
    normalized_path: str = ""
    normalizer_request_paths: list[str] = field(default_factory=list)
    normalizer_request_path: str = ""
    validation_report_paths: list[str] = field(default_factory=list)
    validation_report_path: str = ""
    bundle_dir: str = ""
    bundle_manifest_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArtifactPaths":
        return cls(
            optimizer_raw_paths=coerce_str_list(data.get("optimizer_raw_paths", [])),
            optimizer_page_image_paths=coerce_str_list(data.get("optimizer_page_image_paths", [])),
            optimizer_ocr_request_paths=coerce_str_list(data.get("optimizer_ocr_request_paths", [])),
            optimizer_ocr_request_path=coerce_str(data.get("optimizer_ocr_request_path", "")),
            interpreter_request_paths=coerce_str_list(data.get("interpreter_request_paths", [])),
            interpreter_request_path=coerce_str(data.get("interpreter_request_path", "")),
            interpreter_debug_bundle_path=coerce_str(data.get("interpreter_debug_bundle_path", "")),
            structured_paths=coerce_str_list(data.get("structured_paths", [])),
            structured_path=coerce_str(data.get("structured_path", "")),
            normalized_paths=coerce_str_list(data.get("normalized_paths", [])),
            normalized_path=coerce_str(data.get("normalized_path", "")),
            normalizer_request_paths=coerce_str_list(data.get("normalizer_request_paths", [])),
            normalizer_request_path=coerce_str(data.get("normalizer_request_path", "")),
            validation_report_paths=coerce_str_list(data.get("validation_report_paths", [])),
            validation_report_path=coerce_str(data.get("validation_report_path", "")),
            bundle_dir=coerce_str(data.get("bundle_dir", "")),
            bundle_manifest_path=coerce_str(data.get("bundle_manifest_path", "")),
        )

    def clear_normal_outputs(self) -> None:
        self.optimizer_raw_paths = []
        self.optimizer_page_image_paths = []
        self.optimizer_ocr_request_paths = []
        self.optimizer_ocr_request_path = ""
        self.interpreter_request_paths = []
        self.interpreter_request_path = ""
        self.interpreter_debug_bundle_path = ""
        self.structured_paths = []
        self.structured_path = ""
        self.normalized_paths = []
        self.normalized_path = ""
        self.normalizer_request_paths = []
        self.normalizer_request_path = ""
        self.validation_report_paths = []
        self.validation_report_path = ""


@dataclass
class DocumentRecord:
    content_hash: str = ""
    file_name: str = ""
    relative_path: str = ""
    original_source_path: str = ""
    source_path: str = ""
    current_location: str = "input"
    status: str = "pending"
    final_disposition: str = ""
    attempts: int = 0
    failed_attempts: int = 0
    normalizer_failed_attempts: int = 0
    last_stage: str = ""
    last_error: str = ""
    review_reason: str = ""
    interpreter_needs_review: bool = False
    interpreter_review_reason: str = ""
    validator_needs_review: bool = False
    validator_review_reason: str = ""
    normalizer_needs_review: bool = False
    normalizer_review_reason: str = ""
    route_family: str = ""
    optimizer_profile: str = ""
    interpreter_profile: str = ""
    optimizer_module_key: str = ""
    interpreter_module_key: str = ""
    intake_reason: str = ""
    artifacts: ArtifactPaths = field(default_factory=ArtifactPaths)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    last_processed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["artifacts"] = self.artifacts.to_dict()
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DocumentRecord":
        return cls(
            content_hash=coerce_str(data.get("content_hash", "")),
            file_name=coerce_str(data.get("file_name", "")),
            relative_path=coerce_str(data.get("relative_path", "")),
            original_source_path=coerce_str(data.get("original_source_path", "")),
            source_path=coerce_str(data.get("source_path", "")),
            current_location=coerce_str(data.get("current_location", "input")),
            status=coerce_str(data.get("status", "pending")),
            final_disposition=coerce_str(data.get("final_disposition", "")),
            attempts=coerce_int(data.get("attempts", 0), 0, minimum=0),
            failed_attempts=coerce_int(data.get("failed_attempts", 0), 0, minimum=0),
            normalizer_failed_attempts=coerce_int(data.get("normalizer_failed_attempts", 0), 0, minimum=0),
            last_stage=coerce_str(data.get("last_stage", "")),
            last_error=coerce_str(data.get("last_error", "")),
            review_reason=coerce_str(data.get("review_reason", "")),
            interpreter_needs_review=coerce_bool(data.get("interpreter_needs_review", False), False),
            interpreter_review_reason=coerce_str(data.get("interpreter_review_reason", "")),
            validator_needs_review=coerce_bool(data.get("validator_needs_review", False), False),
            validator_review_reason=coerce_str(data.get("validator_review_reason", "")),
            normalizer_needs_review=coerce_bool(data.get("normalizer_needs_review", False), False),
            normalizer_review_reason=coerce_str(data.get("normalizer_review_reason", "")),
            route_family=coerce_str(data.get("route_family", "")),
            optimizer_profile=_coerce_optimizer_profile(data),
            interpreter_profile=_coerce_interpreter_profile(data),
            optimizer_module_key=coerce_str(data.get("optimizer_module_key", "")),
            interpreter_module_key=coerce_str(data.get("interpreter_module_key", "")),
            intake_reason=coerce_str(data.get("intake_reason", "")),
            artifacts=ArtifactPaths.from_dict(data.get("artifacts", {}) or {}),
            created_at=coerce_str(data.get("created_at", utc_now_iso())),
            updated_at=coerce_str(data.get("updated_at", utc_now_iso())),
            last_processed_at=coerce_str(data.get("last_processed_at", "")),
        )

    def touch(self) -> None:
        self.updated_at = utc_now_iso()


def _coerce_optimizer_profile(data: dict[str, Any]) -> str:
    profile = coerce_str(data.get("optimizer_profile", ""))
    if profile in {"vision", "file"}:
        return profile
    module_key = coerce_str(data.get("optimizer_module_key", ""))
    return "vision" if module_key == "optimizer" else ""


def _coerce_interpreter_profile(data: dict[str, Any]) -> str:
    profile = coerce_str(data.get("interpreter_profile", ""))
    if profile in {"vision", "file", "table"}:
        return profile
    module_key = coerce_str(data.get("interpreter_module_key", ""))
    return "vision" if module_key == "interpreter" else ""


@dataclass
class PipelineState:
    version: int = 1
    updated_at: str = field(default_factory=utc_now_iso)
    documents: dict[str, DocumentRecord] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "updated_at": self.updated_at,
            "documents": {key: value.to_dict() for key, value in self.documents.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PipelineState":
        raw_documents = data.get("documents", {}) or {}
        if not isinstance(raw_documents, dict):
            raw_documents = {}
        documents = {
            str(key): DocumentRecord.from_dict(value)
            for key, value in raw_documents.items()
            if isinstance(value, dict)
        }
        return cls(
            version=coerce_int(data.get("version", 1), 1, minimum=1),
            updated_at=coerce_str(data.get("updated_at", utc_now_iso())),
            documents=documents,
        )
