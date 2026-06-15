from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Mapping

from semantic_control_kernel.types.batch_common import JsonObject


@dataclass(frozen=True)
class PipelineInputFile:
    input_file_id: str
    input_relative_path: str
    original_ref: str
    content_hash: str
    size_bytes: int
    source_kind: str
    ingest_route: str
    pre_run_location: str
    post_run_original_location: str

    SCHEMA_VERSION: ClassVar[str] = "kernel.pipeline_input_file.v1"

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "PipelineInputFile":
        return cls(
            input_file_id=str(payload["input_file_id"]),
            input_relative_path=str(payload["input_relative_path"]),
            original_ref=str(payload["original_ref"]),
            content_hash=str(payload["content_hash"]),
            size_bytes=int(payload["size_bytes"]),
            source_kind=str(payload["source_kind"]),
            ingest_route=str(payload["ingest_route"]),
            pre_run_location=str(payload["pre_run_location"]),
            post_run_original_location=str(payload["post_run_original_location"]),
        )

    def to_manifest_entry(self) -> JsonObject:
        return {
            "input_file_id": self.input_file_id,
            "input_relative_path": self.input_relative_path,
            "original_ref": self.original_ref,
            "content_hash": self.content_hash,
            "size_bytes": self.size_bytes,
            "source_kind": self.source_kind,
            "ingest_route": self.ingest_route,
            "pre_run_location": self.pre_run_location,
            "post_run_original_location": self.post_run_original_location,
        }
