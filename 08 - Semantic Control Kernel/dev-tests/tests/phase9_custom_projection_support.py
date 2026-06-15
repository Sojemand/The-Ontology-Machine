from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from _phase9_fakes import FakeSemanticReleaseAdapter, load_default_release_fixture, ok_result, stable_hash


def staged_taxonomy_ref() -> dict:
    return {
        "component_kind": "taxonomy",
        "stage_id": "tax_stage",
        "artifact_ref": {"artifact_path": "Semantic Release/staged/taxonomy/tax_stage"},
        "component_identity": load_default_release_fixture()["taxonomy_ref"],
        "fingerprint": "taxonomy-default-fingerprint",
        "validation_status": "validated",
    }


def write_full_release_fixture(target) -> Path:
    release_path = Path(target.semantic_release_path) / "releases" / "semantic_release.default" / "release.json"
    release_path.parent.mkdir(parents=True, exist_ok=True)
    release_path.write_text(json.dumps(_full_release_payload(), sort_keys=True), encoding="utf-8")
    return release_path


class NestedCustomReleaseAdapter(FakeSemanticReleaseAdapter):
    def create_custom_semantic_release(self, request_payload: Mapping[str, Any] | None = None):
        payload = dict(request_payload or {})
        self.calls.append("create_custom_semantic_release")
        self.last_payloads.setdefault("create_custom_semantic_release", []).append(payload)
        release_ref = {
            "release_id": "custom.release.nested",
            "release_version": "1.0.0",
            "release_fingerprint": "candidate-fingerprint",
            "taxonomy_ref": payload["staged_taxonomy_ref"]["component_identity"],
            "projection_refs": [payload["staged_projection_ref"]["component_identity"]],
            "runtime_locale": "en",
        }
        return ok_result(
            "create_custom_semantic_release",
            {
                "semantic_release_id": release_ref["release_id"],
                "semantic_release_version": release_ref["release_version"],
                "release_fingerprint": release_ref["release_fingerprint"],
                "release_ref": release_ref,
            },
        )

    def write_semantic_release(self, request_payload: Mapping[str, Any] | None = None):
        self.last_payloads.setdefault("write_semantic_release", []).append(dict(request_payload or {}))
        return super().write_semantic_release(request_payload)


class MinimalTaxonomyIdentityAdapter(FakeSemanticReleaseAdapter):
    def create_custom_taxonomy(self, request_payload: Mapping[str, Any] | None = None):
        update_state = request_payload["update_state"]
        taxonomy_core = update_state["taxonomy_core"]
        taxonomy_id = "custom.taxonomy.minimal.v1"
        fingerprint = stable_hash(json.dumps(taxonomy_core, sort_keys=True))
        return self._maybe(
            "create_custom_taxonomy",
            {
                "taxonomy_id": taxonomy_id,
                "taxonomy_fingerprint": fingerprint,
                "component_identity": {
                    "taxonomy_id": taxonomy_id,
                    "taxonomy_fingerprint": fingerprint,
                    "runtime_locale": "en",
                },
                "fingerprint": fingerprint,
            },
        )


def _full_release_payload() -> dict:
    return {
        "release_id": "semantic_release.default",
        "release_version": "2026-03-28.v6",
        "master_taxonomy_release_id": "taxonomy-default-fingerprint",
        "runtime_locale": "en",
        "master_taxonomy": {
            "taxonomy_id": "normalizer_taxonomy.master",
            "taxonomy_version": "2026-03-28.v6",
            "defaults": {"fallback_document_type": "other"},
            "promotion_slots": [{"slot": "counterparty", "value_type": "string"}],
            "domains": [{"id": "finance", "label": "Finance", "description": "Money documents"}],
            "document_types": [{"code": "invoice", "label": "Invoice", "description": "Payment request"}],
            "categories": [{"code": "finance", "label": "Finance"}],
            "subcategories": [{"code": "other", "label": "Other"}],
            "field_codes": [
                {"code": "issuer", "label": "Issuer"},
                {"code": "amount_due", "label": "Amount due"},
                {"code": "other", "label": "Other"},
            ],
            "row_types": [{"code": "line_item", "label": "Line item"}],
            "cell_codes": [{"code": "description", "label": "Description"}],
        },
    }
