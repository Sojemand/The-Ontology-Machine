from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from phase12_merge_entry_results import blocked_precondition, missing_release, ok_result, owner_error

class FakeSemanticReleaseAdapter:
    def __init__(
        self,
        *,
        missing_create: bool = False,
        nested_create_output: bool = False,
        materialized_fingerprint: str = "",
        fail_load: bool = False,
    ) -> None:
        self.fail_load = fail_load
        self.missing_create = missing_create
        self.nested_create_output = nested_create_output
        self.materialized_fingerprint = materialized_fingerprint
        self.calls: list[str] = []
        self.request_payloads: dict[str, list[dict[str, Any]]] = {}

    def create_custom_semantic_release(self, request_payload: Mapping[str, Any] | None = None):
        self.calls.append("create_custom_semantic_release")
        self.request_payloads.setdefault("create_custom_semantic_release", []).append(dict(request_payload or {}))
        if self.missing_create:
            return missing_release("create_custom_semantic_release")
        if not isinstance(request_payload.get("taxonomy_ref"), Mapping) or not isinstance(request_payload.get("projection_refs"), list):
            return blocked_precondition(
                "create_custom_semantic_release",
                summary="Custom semantic release creation requires taxonomy_ref and projection_refs.",
                missing_fields=("taxonomy_ref", "projection_refs"),
            )
        release_id = str(dict(request_payload.get("semantic_merge_package") or {}).get("release_id") or "merged.release")
        release_ref = {
            "projection_refs": [dict(item) for item in request_payload.get("projection_refs", []) if isinstance(item, Mapping)],
            "release_fingerprint": "sha256:merged",
            "release_id": release_id,
            "release_version": "1.0.0",
            "runtime_locale": str(dict(request_payload.get("taxonomy_ref") or {}).get("runtime_locale") or "en"),
            "taxonomy_ref": dict(request_payload.get("taxonomy_ref") or {}),
        }
        output = dict(release_ref)
        if self.nested_create_output:
            output = {
                "release_fingerprint": release_ref["release_fingerprint"],
                "release_ref": release_ref,
                "semantic_release_id": release_id,
                "semantic_release_version": "1.0.0",
            }
        return ok_result("create_custom_semantic_release", output)

    def write_semantic_release(self, request_payload: Mapping[str, Any] | None = None):
        self.calls.append("write_semantic_release")
        self.request_payloads.setdefault("write_semantic_release", []).append(dict(request_payload or {}))
        if not request_payload or not request_payload.get("release_path") or not isinstance(request_payload.get("release_ref"), Mapping):
            return blocked_precondition(
                "write_semantic_release",
                summary="Semantic release writing requires release_path and release_ref.",
                missing_fields=("release_path", "release_ref"),
            )
        release_file = Path(str(request_payload["release_path"]))
        if release_file.suffix.casefold() != ".json":
            release_file = release_file / "release.json"
        release_file.parent.mkdir(parents=True, exist_ok=True)
        release_ref = dict(request_payload["release_ref"])
        if self.materialized_fingerprint:
            release_ref["release_fingerprint"] = self.materialized_fingerprint
        release_file.write_text(json.dumps(release_ref, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return ok_result(
            "write_semantic_release",
            {
                "release_fingerprint": release_ref.get("release_fingerprint"),
                "release_id": release_ref.get("release_id"),
                "release_path": str(release_file),
                "release_ref": release_ref,
                "release_version": release_ref.get("release_version"),
            },
        )

    def load_semantic_release(self, request_payload: Mapping[str, Any] | None = None):
        self.calls.append("load_semantic_release")
        self.request_payloads.setdefault("load_semantic_release", []).append(dict(request_payload or {}))
        if self.fail_load:
            return owner_error(
                "corpus_builder_load_semantic_release",
                [{"code": "active_snapshot_missing_before_activation"}],
            )
        if not request_payload or not request_payload.get("release_path"):
            return blocked_precondition(
                "corpus_builder_load_semantic_release",
                summary="Semantic release attach requires release_path.",
                missing_fields=("release_path",),
            )
        release_file = Path(str(request_payload["release_path"]))
        if release_file.suffix.casefold() != ".json":
            return owner_error(
                "corpus_builder_load_semantic_release",
                [{"code": "release_path_must_be_json", "release_path": str(release_file)}],
            )
        if not release_file.is_file():
            return owner_error("corpus_builder_load_semantic_release", [{"code": "release_missing", "release_path": str(release_file)}])
        payload = json.loads(release_file.read_text(encoding="utf-8"))
        return ok_result(
            "corpus_builder_load_semantic_release",
            {
                "release_fingerprint": payload.get("release_fingerprint", ""),
                "release_id": payload.get("release_id", ""),
                "release_path": str(release_file),
                "release_version": payload.get("release_version", ""),
            },
        )

    def load_semantic_release_from_artifact_tree(self, request_payload: Mapping[str, Any] | None = None):
        self.calls.append("load_semantic_release_from_artifact_tree")
        self.request_payloads.setdefault("load_semantic_release_from_artifact_tree", []).append(dict(request_payload or {}))
        artifact_root = Path(str(request_payload["artifact_root"]))
        release_files = sorted((artifact_root / "Semantic Release" / "releases").glob("*/release.json"))
        if not release_files:
            return owner_error("corpus_builder_load_semantic_release", [{"code": "release_missing"}])
        payload = json.loads(release_files[0].read_text(encoding="utf-8"))
        return ok_result(
            "corpus_builder_load_semantic_release",
            {
                "release_fingerprint": payload.get("release_fingerprint", ""),
                "release_id": payload.get("release_id", ""),
                "release_path": str(release_files[0]),
                "release_version": payload.get("release_version", ""),
            },
        )

    def preflight_semantic_release_activation(self, request_payload: Mapping[str, Any] | None = None):
        self.calls.append("preflight_semantic_release_activation")
        self.request_payloads.setdefault("preflight_semantic_release_activation", []).append(dict(request_payload or {}))
        if not request_payload or not request_payload.get("release_path"):
            return blocked_precondition(
                "activate_semantic_release",
                summary="Semantic release activation preflight requires release_path.",
                missing_fields=("release_path",),
            )
        if Path(str(request_payload["release_path"])).suffix.casefold() != ".json":
            return owner_error("activate_semantic_release", [{"code": "release_path_must_be_json"}])
        if self.materialized_fingerprint and str(dict(request_payload.get("release_ref") or {}).get("release_fingerprint") or "") != self.materialized_fingerprint:
            return owner_error("activate_semantic_release", [{"code": "target_identity_changed", "mismatched_fields": ["release_fingerprint"]}])
        return ok_result("activate_semantic_release", {"preflight_status": "ok"})

    def activate_semantic_release(self, request_payload: Mapping[str, Any] | None = None):
        self.calls.append("activate_semantic_release")
        self.request_payloads.setdefault("activate_semantic_release", []).append(dict(request_payload or {}))
        if not request_payload or not request_payload.get("release_path"):
            return blocked_precondition(
                "activate_semantic_release",
                summary="Semantic release activation requires release_path.",
                missing_fields=("release_path",),
            )
        if Path(str(request_payload["release_path"])).suffix.casefold() != ".json":
            return owner_error("activate_semantic_release", [{"code": "release_path_must_be_json"}])
        if self.materialized_fingerprint and str(dict(request_payload.get("release_ref") or {}).get("release_fingerprint") or "") != self.materialized_fingerprint:
            return owner_error("activate_semantic_release", [{"code": "target_identity_changed", "mismatched_fields": ["release_fingerprint"]}])
        return ok_result("activate_semantic_release", {"activation_status": "active"})
