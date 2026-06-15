from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.debug.trace_context import build_trace_context
from semantic_control_kernel.debug.trace_links import build_trace_link
from semantic_control_kernel.repository.atomic_json import AtomicJsonStore
from semantic_control_kernel.repository.hard_cap import KernelStateHardCapService
from semantic_control_kernel.repository.ids import generate_id, require_state_id
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.validation.debug_validation import validate_trace_context, validate_trace_link

TRACE_LINKS_PER_WORKFLOW_HARD_CAP = 200


def _validate_trace_context_payload(payload: object) -> None:
    if not isinstance(payload, dict):
        raise TypeError("Trace context must be an object.")
    validate_trace_context(payload)


def _validate_trace_links_payload(payload: object) -> None:
    if not isinstance(payload, dict):
        raise TypeError("Trace links file must be an object.")
    if payload.get("schema_version") != "debug.trace_link_snapshot.v1":
        raise ValueError("Trace links file has invalid schema_version.")
    if not isinstance(payload.get("links"), list):
        raise ValueError("Trace links file must contain links.")
    for entry in payload["links"]:
        if not isinstance(entry, dict):
            raise ValueError("Trace link entry must be an object.")
        validate_trace_link(entry)


class TraceLinkStore:
    def __init__(self, paths: StatePaths) -> None:
        self.paths = paths
        self._json = AtomicJsonStore(paths, "trace_store")

    def create_trace_context(
        self,
        *,
        workflow_run_id: str,
        workflow_tool: str,
        started_by: str,
        root_target_identity_ref: Mapping[str, Any] | str,
        state_root_ref: Mapping[str, Any] | str = "state",
        trace_id: str | None = None,
        **optional_fields: Any,
    ) -> dict[str, Any]:
        payload = build_trace_context(
            trace_id=trace_id or generate_id("trace_id"),
            workflow_run_id=workflow_run_id,
            workflow_tool=workflow_tool,
            started_by=started_by,
            root_target_identity_ref=root_target_identity_ref,
            state_root_ref=state_root_ref,
            parent_trace_id=optional_fields.get("parent_trace_id"),
            active_recovery_event_id=optional_fields.get("active_recovery_event_id"),
            active_mirror_event_id=optional_fields.get("active_mirror_event_id"),
            active_support_bundle_id=optional_fields.get("active_support_bundle_id"),
            related_pipeline_run_id=optional_fields.get("related_pipeline_run_id"),
            related_analysis_run_ids=tuple(optional_fields.get("related_analysis_run_ids", ())),
        )
        self._json.write_json(self._trace_context_path(workflow_run_id), payload, validator=_validate_trace_context_payload)
        KernelStateHardCapService(self.paths).prune_debug_trace_workflows()
        return payload

    def ensure_trace_context(
        self,
        *,
        workflow_run_id: str,
        workflow_tool: str,
        started_by: str,
        root_target_identity_ref: Mapping[str, Any] | str,
        state_root_ref: Mapping[str, Any] | str = "state",
    ) -> dict[str, Any]:
        path = self._trace_context_path(workflow_run_id)
        if path.exists():
            return self._json.read_json(path, validator=_validate_trace_context_payload)
        return self.create_trace_context(
            workflow_run_id=workflow_run_id,
            workflow_tool=workflow_tool,
            started_by=started_by,
            root_target_identity_ref=root_target_identity_ref,
            state_root_ref=state_root_ref,
        )

    def has_trace_context(self, workflow_run_id: str) -> bool:
        return self._trace_context_path(workflow_run_id).exists()

    def get_trace_context(self, workflow_run_id: str) -> dict[str, Any]:
        return self._json.read_json(self._trace_context_path(workflow_run_id), validator=_validate_trace_context_payload)

    def append_link(
        self,
        *,
        workflow_run_id: str,
        object_kind: str,
        object_id: str,
        object_ref: Mapping[str, Any] | str,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        context = self.get_trace_context(workflow_run_id)
        payload = build_trace_link(
            trace_id=trace_id or str(context["trace_id"]),
            workflow_run_id=workflow_run_id,
            object_kind=object_kind,
            object_id=object_id,
            object_ref=object_ref,
        )
        snapshot = self._read_links(workflow_run_id, str(context["trace_id"]))
        snapshot["links"].append(payload)
        if len(snapshot["links"]) > TRACE_LINKS_PER_WORKFLOW_HARD_CAP:
            snapshot["links"] = snapshot["links"][-TRACE_LINKS_PER_WORKFLOW_HARD_CAP:]
        self._json.write_json(self._trace_links_path(workflow_run_id), snapshot, validator=_validate_trace_links_payload)
        return payload

    def append_link_once(
        self,
        *,
        workflow_run_id: str,
        object_kind: str,
        object_id: str,
        object_ref: Mapping[str, Any] | str,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        context = self.get_trace_context(workflow_run_id)
        payload = build_trace_link(
            trace_id=trace_id or str(context["trace_id"]),
            workflow_run_id=workflow_run_id,
            object_kind=object_kind,
            object_id=object_id,
            object_ref=object_ref,
        )
        snapshot = self._read_links(workflow_run_id, str(context["trace_id"]))
        existing = next(
            (
                dict(item)
                for item in snapshot["links"]
                if item.get("object_kind") == payload["object_kind"]
                and item.get("object_id") == payload["object_id"]
                and item.get("object_ref") == payload["object_ref"]
            ),
            None,
        )
        if existing is not None:
            return existing
        snapshot["links"].append(payload)
        if len(snapshot["links"]) > TRACE_LINKS_PER_WORKFLOW_HARD_CAP:
            snapshot["links"] = snapshot["links"][-TRACE_LINKS_PER_WORKFLOW_HARD_CAP:]
        self._json.write_json(self._trace_links_path(workflow_run_id), snapshot, validator=_validate_trace_links_payload)
        return payload

    def list_links_for_workflow(self, workflow_run_id: str) -> list[dict[str, Any]]:
        if not self._trace_links_path(workflow_run_id).exists():
            return []
        payload = self._json.read_json(self._trace_links_path(workflow_run_id), validator=_validate_trace_links_payload)
        return [dict(item) for item in payload["links"]]

    def list_links_for_trace(self, trace_id: str) -> list[dict[str, Any]]:
        matches: list[dict[str, Any]] = []
        for path in sorted(self.paths.state_root.glob("debug/traces/*/trace_links.json")):
            payload = self._json.read_json(path, validator=_validate_trace_links_payload)
            if payload.get("trace_id") == trace_id:
                matches.extend(dict(item) for item in payload["links"])
        return matches

    def snapshot_payload(self, workflow_run_id: str) -> dict[str, Any]:
        context = self.get_trace_context(workflow_run_id)
        return self._read_links(workflow_run_id, str(context["trace_id"]))

    def _read_links(self, workflow_run_id: str, trace_id: str) -> dict[str, Any]:
        path = self._trace_links_path(workflow_run_id)
        if path.exists():
            return self._json.read_json(path, validator=_validate_trace_links_payload)
        return {
            "schema_version": "debug.trace_link_snapshot.v1",
            "trace_id": trace_id,
            "workflow_run_id": workflow_run_id,
            "links": [],
        }

    def _trace_dir(self, workflow_run_id: str) -> Path:
        return self.paths.state_root / "debug" / "traces" / require_state_id('workflow_run_id', workflow_run_id)

    def _trace_context_path(self, workflow_run_id: str) -> Path:
        return self._trace_dir(workflow_run_id) / "trace_context.json"

    def _trace_links_path(self, workflow_run_id: str) -> Path:
        return self._trace_dir(workflow_run_id) / "trace_links.json"
