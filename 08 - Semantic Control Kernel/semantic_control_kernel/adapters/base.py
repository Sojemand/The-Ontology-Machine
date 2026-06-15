from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Callable, Mapping

from semantic_control_kernel.adapters.base_identity import AdapterIdentityMixin
from semantic_control_kernel.adapters.base_results import AdapterResultMixin
from semantic_control_kernel.debug.adapter_diagnostics import AdapterDiagnosticRecorder
from semantic_control_kernel.adapters.invocation import AdapterInvocation, OwnerBoundary, invoke_owner_contract
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.types.adapter_results import AdapterCallResult


READ_ONLY_TIMEOUT_SECONDS = 60
SHORT_WRITE_TIMEOUT_SECONDS = 300
SEMANTIC_RELEASE_WRITE_TIMEOUT_SECONDS = 900
# Long owner workflows may span days; None means no wall-clock kill.
LONG_RUNNING_TIMEOUT_SECONDS: float | None = None


class BasePipelineAdapter(AdapterResultMixin, AdapterIdentityMixin):
    adapter_name = "BasePipelineAdapter"

    def __init__(
        self,
        *,
        state_root: str | Path,
        pipeline_root: str | Path | None = None,
        owner_roots: Mapping[str, str | Path] | None = None,
        python_executable: str | Path | None = None,
    ) -> None:
        module_root = Path(__file__).resolve().parents[2]
        resolved_pipeline_root = Path(pipeline_root).resolve(strict=False) if pipeline_root else module_root.parent
        self.state_root = Path(state_root).resolve(strict=False)
        self.paths = StatePaths.from_state_root(self.state_root)
        self.pipeline_root = resolved_pipeline_root
        self.owner_roots = {
            key: Path(value).resolve(strict=False)
            for key, value in (owner_roots or {}).items()
        }
        self.python_executable = Path(python_executable).resolve(strict=False) if python_executable else None
        self._diagnostics = AdapterDiagnosticRecorder(self.paths)

    @staticmethod
    def owner_path_hash(path: str | Path) -> str:
        return "sha256:" + hashlib.sha256(str(Path(path).resolve(strict=False)).encode("utf-8")).hexdigest()

    def owner_root(self, owner_module: str) -> Path:
        if owner_module in self.owner_roots:
            return self.owner_roots[owner_module]
        return self.pipeline_root / owner_module

    def invoke(
        self,
        *,
        kernel_function: str,
        owner_module: str,
        owner_contract_module: str,
        owner_action: str,
        request_payload: Mapping[str, Any] | None,
        capability_status: str,
        timeout_seconds: float | None,
        mutating: bool = False,
        required_target_proof_fields: tuple[str, ...] = (),
        target_identity: Mapping[str, Any] | None = None,
        state_snapshot_identity: Mapping[str, Any] | None = None,
        workflow_run_id: str | None = None,
        progress_callback: Callable[[], None] | None = None,
    ) -> AdapterCallResult:
        started_at = utc_iso()
        boundary = OwnerBoundary(
            owner_module=owner_module,
            owner_module_root=self.owner_root(owner_module),
            owner_contract_module=owner_contract_module,
            owner_action=owner_action,
            adapter_name=self.adapter_name,
            method_name=owner_action,
            capability_status=capability_status,
            timeout_seconds=timeout_seconds,
            mutating=mutating,
            required_target_proof_fields=required_target_proof_fields,
            python_executable=self.python_executable,
        )
        result = invoke_owner_contract(
            AdapterInvocation(
                state_root=self.state_root,
                kernel_function=kernel_function,
                boundary=boundary,
                request_payload=request_payload or {},
                target_identity=target_identity,
                state_snapshot_identity=state_snapshot_identity,
                workflow_run_id=workflow_run_id,
                progress_callback=progress_callback,
            )
        )
        if workflow_run_id:
            payload = result.to_dict()
            adapter_call_id = str(payload.get("adapter_call_id", ""))
            if adapter_call_id:
                self._diagnostics.record_result(
                    workflow_run_id=workflow_run_id,
                    workflow_tool=kernel_function,
                    adapter_name=self.adapter_name,
                    owner_module=owner_module,
                    owner_action=owner_action,
                    adapter_call_id=adapter_call_id,
                    status=result.status,
                    started_at=started_at,
                    request_ref=f"adapter_calls/{adapter_call_id}/request.json",
                    response_ref=f"adapter_calls/{adapter_call_id}/owner_response.raw.json",
                    mutating=mutating,
                    diagnostics=payload.get("diagnostics", []),
                    target_identity=target_identity,
                )
        return result
