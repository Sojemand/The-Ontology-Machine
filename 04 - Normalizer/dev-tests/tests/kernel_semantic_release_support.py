from __future__ import annotations

import hashlib
import json
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2]


def owner_request(owner_action: str, **fields: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "kernel.pipeline_owner_request.v1",
        "owner_action": owner_action,
        "workflow_run_id": "wr_norm",
        "adapter_call_id": "adc_norm",
        "requested_at": "2026-05-06T00:00:00Z",
        "target_identity": {},
        **fields,
    }
    payload["request_fingerprint"] = request_fingerprint(payload)
    return payload


def request_fingerprint(payload: dict[str, object]) -> str:
    seed = dict(payload)
    seed["request_fingerprint"] = ""
    canonical = json.dumps(seed, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


def sectioned_taxonomy_update_state() -> dict:
    return {
        "schema_version": "kernel.create_taxonomy_update_state.input.v1",
        "taxonomy_id": "taxonomy_sectioned",
        "taxonomy_core": {
            "domains": [{"code": "finance"}, {"code": "other"}],
            "document_types": [{"code": "invoice"}, {"code": "other"}],
            "categories": [{"code": "finance"}, {"code": "other"}],
            "subcategories": [{"code": "other"}],
            "field_codes": [{"code": "issuer"}, {"code": "amount_due"}, {"code": "other"}],
            "row_types": [{"code": "line_item"}, {"code": "other"}],
            "cell_codes": [{"code": "description"}, {"code": "other"}],
            "fallback_codes": {
                "document_type": "other",
                "category": "other",
                "subcategory": "other",
                "field_code": "other",
                "row_type": "other",
                "cell_code": "other",
            },
        },
        "taxonomy_text": {"locale": "en", "terms": {}},
        "semantic_binding": {
            "field_codes": [{"code": "amount_due", "promotion_slot": "amount_due"}],
            "row_types": [{"code": "line_item", "role_type": "document_fact"}],
            "cell_codes": [{"code": "description", "attribute_code": "description"}],
        },
        "runtime_locale": "en",
    }
