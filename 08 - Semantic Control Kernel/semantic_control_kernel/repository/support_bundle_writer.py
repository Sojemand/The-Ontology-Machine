from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from semantic_control_kernel.debug.redaction import RedactionEngine, RedactionProfile
from semantic_control_kernel.debug.retention import SupportBundleRetentionPolicy
from semantic_control_kernel.debug.support_bundle_schema import (
    INCLUDED_REFS_SCHEMA_VERSION,
    SUPPORT_BUNDLE_REQUIRED_FILES,
    TRACE_LINK_SNAPSHOT_SCHEMA_VERSION,
)
from semantic_control_kernel.repository.atomic_json import AtomicJsonStore, atomic_write_text
from semantic_control_kernel.repository.hard_cap import KernelStateHardCapService
from semantic_control_kernel.repository.ids import generate_id, require_state_id
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.support_bundle_payloads import (
    add_optional_manifest_fields,
    manifest_payload,
    support_ref_payload,
)
from semantic_control_kernel.repository.support_bundle_index_ops import (
    append_index,
    default_retention_class,
    safe_summary_markdown,
)
from semantic_control_kernel.repository.support_bundle_refs import included_ref_payload
from semantic_control_kernel.repository.support_bundle_validation import (
    validate_manifest_payload,
    validate_redaction_report_payload,
)
from semantic_control_kernel.repository.trace_store import TraceLinkStore
from semantic_control_kernel.types.recovery import SupportBundleRef
from semantic_control_kernel.validation.debug_validation import validate_support_bundle_manifest
from semantic_control_kernel.validation.recovery_validation import validate_support_bundle_ref


def write_support_bundle_record(
    *,
    paths: StatePaths,
    json_store: AtomicJsonStore,
    trace_store: TraceLinkStore,
    redaction: RedactionEngine,
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
    bundle_id = require_state_id("support_bundle_id", support_bundle_id or generate_id("support_bundle_id"))
    bundle_dir = paths.support_bundles_dir / bundle_id
    manifest_path = bundle_dir / "support_bundle_manifest.json"
    created_at = utc_iso()
    profile = dict(redaction_profile or redaction.profile_payload(RedactionProfile.SUPPORT_SAFE_V1))
    safe_summary_text = redaction.safe_summary(summary)
    redaction.assert_safe_summary(safe_summary_text)
    included_ref_payloads = [included_ref_payload(item, paths) for item in included_refs]
    redacted_context, stats = redaction.redact(dict(technical_context or {}), profile_id=profile["profile_id"])
    trace_context = trace_store.ensure_trace_context(
        workflow_run_id=workflow_run_id,
        workflow_tool=workflow_tool,
        started_by=created_by or "support_bundle_store",
        root_target_identity_ref=f"workflow_runs/active/{workflow_run_id}.json#target_identity",
        state_root_ref="state",
    )
    retention = retention_class or default_retention_class(category)
    expires_at = SupportBundleRetentionPolicy.expires_at_for(created_at=created_at, retention_class=retention)
    redaction_report = redaction.build_report(support_bundle_id=bundle_id, profile_id=profile["profile_id"], stats=stats, created_at=created_at)
    redaction_report_path = paths.debug_redaction_reports_dir / f"{bundle_id}.json"
    manifest = manifest_payload(
        bundle_id=bundle_id,
        trace_id=trace_context["trace_id"],
        created_at=created_at,
        category=category,
        severity=severity,
        workflow_run_id=workflow_run_id,
        workflow_tool=workflow_tool,
        safe_summary_text=safe_summary_text,
        included_ref_payloads=included_ref_payloads,
        profile=profile,
        retention=retention,
        redaction_report_ref=paths.relative_to_state_root(redaction_report_path),
    )
    add_optional_manifest_fields(
        manifest,
        redaction=redaction,
        profile=profile,
        expires_at=expires_at,
        recovery_event_id=recovery_event_id,
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
        created_by=created_by,
    )
    validate_support_bundle_manifest(manifest)
    json_store.write_json(manifest_path, manifest, immutable=True, validator=validate_manifest_payload)
    trace_store.append_link_once(workflow_run_id=workflow_run_id, object_kind="support_bundle", object_id=bundle_id, object_ref=paths.relative_to_state_root(manifest_path))
    _write_bundle_files(paths, json_store, bundle_dir, bundle_id, manifest, included_ref_payloads, trace_store.snapshot_payload(workflow_run_id), redaction_report, redaction_report_path)
    payload = support_ref_payload(
        bundle_id,
        paths.relative_to_state_root(manifest_path),
        created_at,
        category,
        workflow_run_id,
        recovery_event_id,
        safe_summary_text,
        included_ref_payloads,
        profile,
    )
    validate_support_bundle_ref(payload)
    append_index(paths.support_index_path, json_store, payload)
    KernelStateHardCapService(paths).prune_support_bundles()
    return SupportBundleRef(payload)


def _write_bundle_files(
    paths: StatePaths,
    json_store: AtomicJsonStore,
    bundle_dir: Path,
    bundle_id: str,
    manifest: Mapping[str, Any],
    included_ref_payloads: Sequence[Mapping[str, Any] | str],
    trace_links_payload: Mapping[str, Any],
    redaction_report: Mapping[str, Any],
    redaction_report_path: Path,
) -> None:
    json_store.write_json(bundle_dir / "included_refs.json", {"schema_version": INCLUDED_REFS_SCHEMA_VERSION, "support_bundle_id": bundle_id, "included_refs": included_ref_payloads}, immutable=True)
    paths.require_under_state_root(bundle_dir / "safe_summary.md")
    atomic_write_text(bundle_dir / "safe_summary.md", safe_summary_markdown(manifest), temp_dir=paths.tmp_dir)
    json_store.write_json(bundle_dir / "trace_links.json", {"schema_version": TRACE_LINK_SNAPSHOT_SCHEMA_VERSION, **dict(trace_links_payload)}, immutable=True)
    json_store.write_json(redaction_report_path, redaction_report, immutable=True, validator=validate_redaction_report_payload)
    json_store.write_json(bundle_dir / "redaction_report.json", redaction_report, immutable=True)
    for required_file in SUPPORT_BUNDLE_REQUIRED_FILES:
        if not (bundle_dir / required_file).exists():
            raise ValueError(f"Support bundle missing required file: {required_file}")
