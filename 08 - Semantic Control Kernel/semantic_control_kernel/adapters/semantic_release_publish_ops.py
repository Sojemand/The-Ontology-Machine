from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.adapters.base import READ_ONLY_TIMEOUT_SECONDS, SEMANTIC_RELEASE_WRITE_TIMEOUT_SECONDS, SHORT_WRITE_TIMEOUT_SECONDS
from semantic_control_kernel.adapters.semantic_release_refs import (
    artifact_root_from_semantic_release_folder,
    requires_detached_custom_release_write,
)
from semantic_control_kernel.types.adapter_results import AdapterCallResult


class SemanticReleasePublishMixin:
    def build_runtime_semantic_assets(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult:
        return self.invoke(
            kernel_function="build_runtime_semantic_assets",
            owner_module="04 - Normalizer",
            owner_contract_module="normalizer_vision.orchestrator_contract",
            owner_action="build_runtime_semantic_assets",
            request_payload=request_payload,
            capability_status="implemented_in_pipeline",
            timeout_seconds=SEMANTIC_RELEASE_WRITE_TIMEOUT_SECONDS,
        )

    def write_semantic_release(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult:
        payload = dict(request_payload or {})
        release_ref = dict(payload.get("release_ref") or {})
        release_path = str(payload.get("release_path") or "").strip()
        output_path = _release_json_path(release_path)
        if requires_detached_custom_release_write(payload, release_ref):
            return self._write_detached_custom_release(payload, release_ref, output_path)
        return self._publish_default_semantic_release(payload, release_ref, output_path)

    def _write_detached_custom_release(
        self,
        payload: Mapping[str, Any],
        release_ref: Mapping[str, Any],
        output_path: str,
    ) -> AdapterCallResult:
        semantic_release_folder = str(payload.get("semantic_release_path") or payload.get("semantic_release_folder") or "")
        artifact_root_path = artifact_root_from_semantic_release_folder(semantic_release_folder)
        target_identity = self.target_identity(payload, artifact_root_path=artifact_root_path)
        owner_request = self.phase19_request(
            owner_action="materialize_semantic_release_candidate",
            request_payload=payload,
            target_identity=target_identity,
            release_ref=release_ref,
            output_path=output_path,
            base_release_path=str(payload.get("base_release_path") or ""),
            projection_update_state=dict(payload.get("projection_update_state") or {}),
            staged_projection_ref=dict(payload.get("staged_projection_ref") or {}),
            runtime_locale=str(payload.get("runtime_locale") or release_ref.get("runtime_locale") or ""),
        )
        return self.invoke(
            kernel_function="write_semantic_release",
            owner_module="04 - Normalizer",
            owner_contract_module="normalizer_vision.edit_contract",
            owner_action="materialize_semantic_release_candidate",
            request_payload=owner_request,
            capability_status="kernel_composition_over_existing_primitives",
            timeout_seconds=SEMANTIC_RELEASE_WRITE_TIMEOUT_SECONDS,
            mutating=True,
            required_target_proof_fields=("release_fingerprint",),
            target_identity=target_identity,
        )

    def _publish_default_semantic_release(
        self,
        payload: Mapping[str, Any],
        release_ref: Mapping[str, Any],
        output_path: str,
    ) -> AdapterCallResult:
        projection_ids = [
            str(item.get("projection_id"))
            for item in release_ref.get("projection_refs", ())
            if isinstance(item, Mapping) and item.get("projection_id")
        ]
        taxonomy_ref = release_ref.get("taxonomy_ref") if isinstance(release_ref.get("taxonomy_ref"), Mapping) else {}
        owner_request = {
            "action": "publish_semantic_release",
            "output_path": output_path,
            "release_id": str(release_ref.get("release_id") or "") or None,
            "release_version": str(release_ref.get("release_version") or "") or None,
            "projection_ids": projection_ids,
            "target_locale": str(release_ref.get("runtime_locale") or taxonomy_ref.get("runtime_locale") or "") or None,
        }
        owner_request = {key: value for key, value in owner_request.items() if value not in (None, "", [])}
        return self.invoke(
            kernel_function="write_semantic_release",
            owner_module="04 - Normalizer",
            owner_contract_module="normalizer_vision.orchestrator_contract",
            owner_action="publish_semantic_release",
            request_payload=owner_request,
            capability_status="kernel_composition_over_existing_primitives",
            timeout_seconds=SEMANTIC_RELEASE_WRITE_TIMEOUT_SECONDS,
            mutating=True,
            required_target_proof_fields=("release_fingerprint",),
            target_identity=self.target_identity(payload, release_ref=release_ref),
        )

    def export_default_semantic_release(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult:
        payload = dict(request_payload or {})
        blueprint_ref = str(payload.get("blueprint_ref") or "default").strip()
        if blueprint_ref in {"default_blueprint", "default-blueprint"}:
            blueprint_ref = "default"
        semantic_release_path = str(payload.get("semantic_release_path") or "").strip()
        output_path = str(payload.get("output_path") or "").strip()
        if not output_path and semantic_release_path:
            output_path = str(Path(semantic_release_path) / "default_semantic_release.export.json")
        owner_request = {"action": "export_default_blueprint_release", "blueprint_ref": blueprint_ref}
        if output_path:
            owner_request["output_path"] = output_path
        return self.invoke(
            kernel_function="export_default_semantic_release",
            owner_module="04 - Normalizer",
            owner_contract_module="normalizer_vision.orchestrator_contract",
            owner_action="export_default_blueprint_release",
            request_payload=owner_request,
            capability_status="kernel_composition_over_existing_primitives",
            timeout_seconds=SEMANTIC_RELEASE_WRITE_TIMEOUT_SECONDS,
            mutating=True,
            required_target_proof_fields=("release_fingerprint",),
            target_identity=payload.get("target_identity") if isinstance(payload.get("target_identity"), Mapping) else None,
        )

    def load_semantic_release(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult:
        payload = dict(request_payload or {})
        return self._load_semantic_release_payload(payload)

    def load_semantic_release_from_artifact_tree(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult:
        payload = dict(request_payload or {})
        if "release_path" not in payload and payload.get("artifact_root"):
            payload["release_path"] = str(payload["artifact_root"]).rstrip("/\\") + "/Semantic Release"
        return self._load_semantic_release_payload(payload)

    def _load_semantic_release_payload(self, payload: Mapping[str, Any]) -> AdapterCallResult:
        return self.invoke(
            kernel_function="corpus_builder_load_semantic_release",
            owner_module="05 - Corpus Builder",
            owner_contract_module="corpus_builder.orchestrator_contract",
            owner_action="load_semantic_release",
            request_payload={
                "action": "load_semantic_release",
                "release_path": _release_json_path(str(payload.get("release_path") or "")),
                "corpus_db_path": str(payload.get("corpus_db_path") or ""),
                "write_global_mirrors": bool(payload.get("write_global_mirrors", False)),
            },
            capability_status="implemented_in_pipeline",
            timeout_seconds=READ_ONLY_TIMEOUT_SECONDS,
        )

    def preflight_semantic_release_activation(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult:
        payload = dict(request_payload or {})
        return self.invoke(
            kernel_function="activate_semantic_release",
            owner_module="05 - Corpus Builder",
            owner_contract_module="corpus_builder.orchestrator_contract",
            owner_action="activation_preflight",
            request_payload={"action": "activation_preflight", "release_path": _release_json_path(str(payload.get("release_path") or "")), "corpus_db_path": str(payload.get("corpus_db_path") or "")},
            capability_status="implemented_in_pipeline",
            timeout_seconds=READ_ONLY_TIMEOUT_SECONDS,
        )

    def activate_semantic_release(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult:
        payload = dict(request_payload or {})
        release_ref = dict(payload.get("release_ref") or {})
        return self.invoke(
            kernel_function="activate_semantic_release",
            owner_module="05 - Corpus Builder",
            owner_contract_module="corpus_builder.orchestrator_contract",
            owner_action="activate_semantic_release",
            request_payload={"action": "activate_semantic_release", "release_path": _release_json_path(str(payload.get("release_path") or "")), "corpus_db_path": str(payload.get("corpus_db_path") or ""), "write_global_mirrors": bool(payload.get("write_global_mirrors", False))},
            capability_status="implemented_in_pipeline",
            timeout_seconds=SHORT_WRITE_TIMEOUT_SECONDS,
            mutating=True,
            required_target_proof_fields=("database_path|database_path_hash", "release_fingerprint"),
            target_identity=self.target_identity(payload, release_ref=release_ref),
        )


def _release_json_path(release_path: str) -> str:
    path = str(release_path or "").strip()
    if path and not path.casefold().endswith(".json"):
        return str(Path(path) / "release.json")
    return path
