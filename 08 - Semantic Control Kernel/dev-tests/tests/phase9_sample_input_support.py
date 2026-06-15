from __future__ import annotations

import json
from pathlib import Path

from semantic_control_kernel.types.adapter_results import AdapterCallResult


class FakeOrchestratorAdapter:
    def __init__(self, raw_root: Path) -> None:
        self.raw_root = raw_root
        self.requests: list[dict] = []

    def inspect_source_sample(self, request_payload):
        payload = dict(request_payload)
        self.requests.append(payload)
        source_path = Path(payload["source_document_path"])
        raw_path = self.raw_root / f"{source_path.stem}.raw.json"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(json.dumps(_optimizer_raw_payload(source_path)), encoding="utf-8")
        return AdapterCallResult(
            {
                "adapter_call_id": "acl_fake_sample",
                "adapter_name": "FakeOrchestratorAdapter",
                "capability_status": "implemented_in_pipeline",
                "diagnostics": [],
                "kernel_function": "inspect_source_sample",
                "output_refs": {"raw_extract_paths": [str(raw_path)]},
                "receipt_fields": {},
                "status": "ok",
                "target_identity_proof": {},
            }
        )


class FailingOrchestratorAdapter:
    def inspect_source_sample(self, _request_payload):
        return AdapterCallResult(
            {
                "adapter_call_id": "acl_fake_sample_fail",
                "adapter_name": "FailingOrchestratorAdapter",
                "capability_status": "implemented_in_pipeline",
                "diagnostics": [{"code": "owner_response_error", "summary": "optimizer_ocr Modell fehlt."}],
                "kernel_function": "inspect_source_sample",
                "output_refs": {},
                "receipt_fields": {},
                "status": "owner_error",
                "target_identity_proof": {},
            }
        )


def _optimizer_raw_payload(source_path: Path) -> dict:
    return {
        "schema_version": "optimizer_raw_v2",
        "optimizer_profile": "file",
        "source": {
            "file_name": source_path.name,
            "file_ext": source_path.suffix,
            "content_hash": "sha256:sample",
            "page_count": 1,
            "document_type": "invoice",
            "language": "de",
        },
        "context": {"page_number": 1, "document_page_count": 1},
        "ocr_reference": {
            "blocks": [
                {
                    "id": "p1_b1",
                    "type": "paragraph",
                    "layout_label": "header",
                    "value": "Rechnung RE-2026-001",
                    "position": {"page": 1},
                }
            ]
        },
    }
