from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping


@dataclass(frozen=True)
class OwnerBoundary:
    owner_module: str
    owner_module_root: Path
    owner_contract_module: str
    owner_action: str
    adapter_name: str
    method_name: str
    capability_status: str
    timeout_seconds: float | None
    mutating: bool = False
    required_target_proof_fields: tuple[str, ...] = ()
    python_executable: Path | None = None


@dataclass(frozen=True)
class AdapterInvocation:
    state_root: Path
    kernel_function: str
    boundary: OwnerBoundary
    request_payload: Mapping[str, Any]
    target_identity: Mapping[str, Any] | None = None
    state_snapshot_identity: Mapping[str, Any] | None = None
    workflow_run_id: str | None = None
    progress_callback: Callable[[], None] | None = None
