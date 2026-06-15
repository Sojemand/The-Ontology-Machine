from __future__ import annotations

import shutil
from typing import Any, Mapping, Sequence

from semantic_control_kernel.debug.redaction import RedactionEngine
from semantic_control_kernel.repository.atomic_json import AtomicJsonStore
from semantic_control_kernel.repository.ids import require_state_id
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.support_bundle_index_ops import (
    SUPPORT_REF_KEYS,
    remove_from_index,
)
from semantic_control_kernel.repository.support_bundle_validation import (
    validate_manifest_payload,
    validate_redaction_report_payload,
    validate_support_ref_payload,
)
from semantic_control_kernel.repository.support_bundle_writer import write_support_bundle_record
from semantic_control_kernel.repository.trace_store import TraceLinkStore
from semantic_control_kernel.types.recovery import SUPPORT_BUNDLE_REF_SCHEMA_VERSION, SupportBundleRef


class SupportBundleStore:
    def __init__(self, paths: StatePaths) -> None:
        self.paths = paths
        self._json = AtomicJsonStore(paths, "support_bundles")
        self._trace_store = TraceLinkStore(paths)
        self._redaction = RedactionEngine(state_root=paths.state_root)

    def write_support_bundle(
        self,
        *,
        category: str,
        workflow_run_id: str,
        recovery_event_id: str | None,
        summary: str,
        included_refs: Sequence[Mapping[str, Any] | str] = (),
        technical_context: Mapping[str, Any] | None = None,
        support_bundle_id: str | None = None,
        workflow_tool: str = "unknown_workflow",
        severity: str | None = None,
        retention_class: str | None = None,
        mirror_event_id: str | None = None,
        failed_kernel_step: str | None = None,
        user_visible_cause: str | None = None,
        state_snapshot_identity: Mapping[str, Any] | None = None,
        target_identity: Mapping[str, Any] | None = None,
        what_was_preserved: str | None = None,
        what_was_not_changed: str | None = None,
        related_receipt_refs: Sequence[Mapping[str, Any]] = (),
        related_progress_event_refs: Sequence[Mapping[str, Any]] = (),
        related_mirror_event_refs: Sequence[Mapping[str, Any]] = (),
        related_recovery_refs: Sequence[Mapping[str, Any]] = (),
        adapter_call_diagnostic_refs: Sequence[Mapping[str, Any]] = (),
        llm_attempt_diagnostic_refs: Sequence[Mapping[str, Any]] = (),
        failed_attempt_artifact_refs: Sequence[Mapping[str, Any]] = (),
        redaction_profile: Mapping[str, Any] | None = None,
        created_by: str | None = None,
    ) -> SupportBundleRef:
        return write_support_bundle_record(
            paths=self.paths,
            json_store=self._json,
            trace_store=self._trace_store,
            redaction=self._redaction,
            category=category,
            workflow_run_id=workflow_run_id,
            recovery_event_id=recovery_event_id,
            summary=summary,
            included_refs=included_refs,
            technical_context=technical_context,
            support_bundle_id=support_bundle_id,
            workflow_tool=workflow_tool,
            severity=severity,
            retention_class=retention_class,
            mirror_event_id=mirror_event_id,
            failed_kernel_step=failed_kernel_step,
            user_visible_cause=user_visible_cause,
            state_snapshot_identity=state_snapshot_identity,
            target_identity=target_identity,
            what_was_preserved=what_was_preserved,
            what_was_not_changed=what_was_not_changed,
            related_receipt_refs=related_receipt_refs,
            related_progress_event_refs=related_progress_event_refs,
            related_mirror_event_refs=related_mirror_event_refs,
            related_recovery_refs=related_recovery_refs,
            adapter_call_diagnostic_refs=adapter_call_diagnostic_refs,
            llm_attempt_diagnostic_refs=llm_attempt_diagnostic_refs,
            failed_attempt_artifact_refs=failed_attempt_artifact_refs,
            redaction_profile=redaction_profile,
            created_by=created_by,
        )

    def get_support_bundle_ref(self, support_bundle_id: str) -> SupportBundleRef:
        support_bundle_id = require_state_id("support_bundle_id", support_bundle_id)
        manifest = self.get_manifest(support_bundle_id)
        manifest_path = self.paths.support_bundles_dir / support_bundle_id / "support_bundle_manifest.json"
        ref_payload = {key: manifest[key] for key in SUPPORT_REF_KEYS if key in manifest}
        ref_payload["schema_version"] = SUPPORT_BUNDLE_REF_SCHEMA_VERSION
        ref_payload["support_bundle_path"] = self.paths.relative_to_state_root(manifest_path)
        ref_payload.setdefault("recovery_event_id", "")
        validate_support_ref_payload(ref_payload)
        return SupportBundleRef(ref_payload)

    def get_manifest(self, support_bundle_id: str) -> dict[str, Any]:
        support_bundle_id = require_state_id("support_bundle_id", support_bundle_id)
        manifest_path = self.paths.support_bundles_dir / support_bundle_id / "support_bundle_manifest.json"
        return self._json.read_json(manifest_path, validator=validate_manifest_payload)

    def list_bundle_manifests(self) -> list[dict[str, Any]]:
        manifests: list[dict[str, Any]] = []
        for path in sorted(self.paths.support_bundles_dir.glob("*/support_bundle_manifest.json")):
            manifests.append(self._json.read_json(path, validator=validate_manifest_payload))
        return manifests

    def bundle_file_refs(self, support_bundle_id: str) -> dict[str, str]:
        support_bundle_id = require_state_id("support_bundle_id", support_bundle_id)
        bundle_dir = self.paths.support_bundles_dir / support_bundle_id
        refs = {
            "manifest_ref": self.paths.relative_to_state_root(bundle_dir / "support_bundle_manifest.json"),
            "included_refs_ref": self.paths.relative_to_state_root(bundle_dir / "included_refs.json"),
            "redaction_report_ref": self.paths.relative_to_state_root(bundle_dir / "redaction_report.json"),
            "trace_links_ref": self.paths.relative_to_state_root(bundle_dir / "trace_links.json"),
            "safe_summary_ref": self.paths.relative_to_state_root(bundle_dir / "safe_summary.md"),
        }
        return refs

    def get_open_bundle_payload(self, support_bundle_id: str) -> dict[str, Any]:
        manifest = self.get_manifest(support_bundle_id)
        refs = self.bundle_file_refs(support_bundle_id)
        return {
            "support_bundle_ref": self.get_support_bundle_ref(support_bundle_id).to_dict(),
            "safe_summary": manifest["safe_summary"],
            "redaction_profile": dict(manifest["redaction_profile"]),
            "manifest_ref": refs["manifest_ref"],
            "included_refs_ref": refs["included_refs_ref"],
            "redaction_report_ref": refs["redaction_report_ref"],
        }

    def delete_bundle(self, support_bundle_id: str) -> bool:
        support_bundle_id = require_state_id("support_bundle_id", support_bundle_id)
        bundle_dir = self.paths.support_bundles_dir / support_bundle_id
        if not bundle_dir.exists():
            return False
        self.paths.require_under_state_root(bundle_dir)
        shutil.rmtree(bundle_dir)
        redaction_report_path = self.paths.debug_redaction_reports_dir / f"{support_bundle_id}.json"
        self._json.delete_json(redaction_report_path)
        remove_from_index(self.paths.support_index_path, self._json, support_bundle_id)
        return True
