from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from semantic_control_kernel.repository.paths import stable_hash
from semantic_control_kernel.workflows.database_creation.shared_steps import write_json_file

from _phase9_results import missing, ok_result
from _phase9_support import (
    codes_from_taxonomy_core,
    included_projection_codes,
    load_default_release_fixture,
    projection_refs_from_component_identity,
)


class FakeSemanticReleaseAdapter:
    def __init__(
        self,
        *,
        default_release: Mapping[str, Any] | None = None,
        missing_methods: Sequence[str] = (),
        invalid_projection_validation: bool = False,
    ) -> None:
        self.default_release = dict(default_release or load_default_release_fixture())
        self.missing_methods = set(missing_methods)
        self.invalid_projection_validation = invalid_projection_validation
        self.calls: list[str] = []
        self.last_payloads: dict[str, list[Mapping[str, Any]]] = {}

    def export_default_semantic_release(self, request_payload: Mapping[str, Any] | None = None):
        return self._maybe("export_default_semantic_release", {"release_ref": self.default_release})

    def write_semantic_release(self, request_payload: Mapping[str, Any] | None = None):
        if "write_semantic_release" in self.missing_methods:
            return missing("write_semantic_release")
        self.calls.append("write_semantic_release")
        release_path = Path(str(request_payload["release_path"]))
        release_path.mkdir(parents=True, exist_ok=True)
        write_json_file(release_path / "release.json", request_payload["release_ref"])
        return ok_result(
            "write_semantic_release",
            {
                "release_path": str(release_path),
                "release_id": request_payload["release_ref"].get("release_id"),
                "release_fingerprint": request_payload["release_ref"].get("release_fingerprint"),
            },
        )

    def load_semantic_release(self, request_payload: Mapping[str, Any] | None = None):
        return self._maybe("load_semantic_release", {"release_path": request_payload.get("release_path", "")})

    def preflight_semantic_release_activation(self, request_payload: Mapping[str, Any] | None = None):
        return self._maybe("preflight_semantic_release_activation", {"validation_status": "passed"})

    def activate_semantic_release(self, request_payload: Mapping[str, Any] | None = None):
        return self._maybe("activate_semantic_release", {"activation_status": "active"})

    def remove_taxonomy_or_projection(self, request_payload: Mapping[str, Any] | None = None):
        payload = dict(request_payload or {})
        self.last_payloads.setdefault("remove_taxonomy_or_projection", []).append(payload)
        release_ref = dict(payload.get("release_ref") or {})
        projection_ref = dict(payload.get("projection_ref") or {})
        removed_projection_id = str(projection_ref.get("projection_id") or "")
        projection_refs = [dict(item) for item in release_ref.get("projection_refs", []) if isinstance(item, Mapping)]
        remaining = [item for item in projection_refs if str(item.get("projection_id") or "") != removed_projection_id]
        removed = [item for item in projection_refs if str(item.get("projection_id") or "") == removed_projection_id]
        updated_release_ref = {
            **release_ref,
            "projection_refs": remaining,
            "release_fingerprint": stable_hash(json.dumps({**release_ref, "projection_refs": remaining}, sort_keys=True)),
        }
        return self._maybe(
            "remove_taxonomy_or_projection",
            {
                "removed_component_kind": payload.get("component_kind"),
                "updated_release_ref": updated_release_ref,
                "removed_projection_refs": removed or ([projection_ref] if projection_ref else []),
                "remaining_projection_refs": remaining,
                "completeness_state": "complete" if remaining else "incomplete",
            },
        )

    def create_custom_taxonomy(self, request_payload: Mapping[str, Any] | None = None):
        update_state = request_payload["update_state"]
        taxonomy_core = update_state["taxonomy_core"]
        taxonomy_ref = {
            "taxonomy_id": "custom.taxonomy.v1",
            "taxonomy_fingerprint": stable_hash(json.dumps(taxonomy_core, sort_keys=True)),
            "allowed_codes": codes_from_taxonomy_core(taxonomy_core),
            "fallback_codes": ["other"],
            "promotion_slots": deepcopy(list(taxonomy_core.get("promotion_slots", []))),
            "runtime_locale": "en",
        }
        return self._maybe(
            "create_custom_taxonomy",
            {
                "taxonomy_id": taxonomy_ref["taxonomy_id"],
                "component_identity": taxonomy_ref,
                "fingerprint": taxonomy_ref["taxonomy_fingerprint"],
                "artifact_ref": {"artifact_path": "semantic-release/custom-taxonomy.json"},
            },
        )

    def stage_taxonomy(self, request_payload: Mapping[str, Any] | None = None):
        payload = dict(request_payload or {})
        self.last_payloads.setdefault("stage_taxonomy", []).append(payload)
        custom_taxonomy = payload.get("custom_taxonomy") or payload
        return self._maybe(
            "stage_taxonomy",
            {
                "stage_id": "stage_taxonomy_001",
                "component_identity": custom_taxonomy.get("component_identity", custom_taxonomy),
                "fingerprint": custom_taxonomy.get("fingerprint", "taxonomy_fingerprint"),
                "artifact_ref": {"artifact_path": "Semantic Release/staged/taxonomy/stage_taxonomy_001"},
            },
        )

    def create_custom_projection(self, request_payload: Mapping[str, Any] | None = None):
        update_state = request_payload["update_state"]
        projection_refs = [
            {
                "projection_id": item["projection_id"],
                "projection_fingerprint": stable_hash(json.dumps(item, sort_keys=True)),
                "included_taxonomy_codes": included_projection_codes(item),
            }
            for item in update_state["projection_precursors"]
            if isinstance(item, Mapping) and item.get("projection_id")
        ]
        projection_ids = [item["projection_id"] for item in projection_refs]
        projection_set_fingerprint = stable_hash(json.dumps(projection_refs, sort_keys=True))
        return self._maybe(
            "create_custom_projection",
            {
                "projection_ids": projection_ids,
                "projection_refs": projection_refs,
                "component_identity": projection_refs[0] if len(projection_refs) == 1 else {"projection_ids": projection_ids, "projection_refs": projection_refs},
                "fingerprint": projection_set_fingerprint,
                "projection_set_fingerprint": projection_set_fingerprint,
                "artifact_ref": {"artifact_path": "semantic-release/custom-projections.json"},
            },
        )

    def validate_projections_against_taxonomy(self, request_payload: Mapping[str, Any] | None = None):
        if "validate_projections_against_taxonomy" in self.missing_methods:
            return missing("validate_projections_against_taxonomy")
        self.calls.append("validate_projections_against_taxonomy")
        status = "invalid" if self.invalid_projection_validation else "validated"
        return ok_result("validate_projections_against_taxonomy", {"validation_status": status})

    def stage_projections(self, request_payload: Mapping[str, Any] | None = None):
        projection = request_payload.get("custom_projection") or request_payload
        return self._maybe(
            "stage_projections",
            {
                "stage_id": "stage_projection_001",
                "component_identity": projection.get("component_identity", {"projection_ids": projection.get("projection_ids", [])}),
                "fingerprint": projection.get("fingerprint", "projection_fingerprint"),
                "artifact_ref": {"artifact_path": "Semantic Release/staged/projections/stage_projection_001"},
            },
        )

    def create_custom_semantic_release(self, request_payload: Mapping[str, Any] | None = None):
        self.last_payloads.setdefault("create_custom_semantic_release", []).append(dict(request_payload or {}))
        projection_refs = projection_refs_from_component_identity(request_payload["staged_projection_ref"]["component_identity"])
        return self._maybe(
            "create_custom_semantic_release",
            {
                "release_id": "custom.release.v1",
                "release_version": "1.0.0",
                "release_fingerprint": stable_hash("custom.release.v1"),
                "taxonomy_ref": request_payload["staged_taxonomy_ref"]["component_identity"],
                "projection_refs": projection_refs,
                "runtime_locale": "en",
            },
        )

    def _maybe(self, method_name: str, output_refs: Mapping[str, Any]):
        if method_name in self.missing_methods:
            return missing(method_name)
        self.calls.append(method_name)
        return ok_result(method_name, output_refs)
