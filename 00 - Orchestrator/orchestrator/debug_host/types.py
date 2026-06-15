"""Named transport types for generic orchestrator debug sessions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import subprocess
from typing import Any

TERMINAL_STATUSES = {"ok", "error", "cancelled"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class DebugStep:
    kind: str
    module_key: str = ""
    action: str = ""
    name: str = ""

    @classmethod
    def module(cls, module_key: str, action: str) -> "DebugStep":
        return cls(kind="module_step", module_key=module_key, action=action)

    @classmethod
    def host(cls, name: str) -> "DebugStep":
        return cls(kind="host_step", name=name)

    @property
    def label(self) -> str:
        return self.name or f"{self.module_key}:{self.action}"


@dataclass(frozen=True)
class DebugDescriptor:
    module_key: str
    display_name: str
    stage_role: str
    supports_batch: bool
    supports_single: bool
    supports_scan: bool
    input_source: str
    output_source: str
    controls: tuple[str, ...]
    artifacts: tuple[str, ...]


@dataclass(frozen=True)
class DebugPlan:
    name: str
    steps: tuple[DebugStep, ...]


@dataclass(frozen=True)
class DebugSessionRequest:
    session_id: str
    module_key: str
    mode: str
    input_root: Path
    source_path: str
    output_root: Path
    session_root: Path
    options: dict[str, Any] = field(default_factory=dict)

    @property
    def logical_source_path(self) -> str:
        source_path = str(self.source_path or "").strip()
        if not source_path:
            return ""
        if Path(source_path).is_absolute():
            return ""
        return source_path.replace("\\", "/").strip("/")

    @property
    def resolved_source_path(self) -> Path | None:
        if not self.source_path:
            return None
        candidate = Path(self.source_path)
        return candidate if candidate.is_absolute() else (self.input_root / candidate)


@dataclass
class DebugSnapshot:
    status: str = "pending"
    stage: str = ""
    detail: str = ""
    updated_at: str = field(default_factory=utc_now_iso)
    processed: int = 0
    total: int = 0
    warnings: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    counters: dict[str, int] = field(default_factory=dict)


@dataclass
class DebugResult:
    status: str = "error"
    summary: str = ""
    artifacts: dict[str, list[str]] = field(default_factory=dict)
    error: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, list[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class DebugCleanupSummary:
    removed_sessions: int = 0


@dataclass
class DebugProcessHandle:
    process: subprocess.Popen[str]
    request_path: Path
    response_path: Path


@dataclass
class DebugSession:
    request: DebugSessionRequest
    descriptor: DebugDescriptor
    plan: DebugPlan
    registry_path: Path | None = None
    current_step_index: int = 0
    active_step: DebugStep | None = None
    process_handle: DebugProcessHandle | None = None
    snapshot: DebugSnapshot | None = None
    result: DebugResult | None = None
    completed_results: list[DebugResult] = field(default_factory=list)

    @property
    def session_root(self) -> Path:
        return self.request.session_root

    @property
    def output_root(self) -> Path:
        return self.request.output_root

    @property
    def request_path(self) -> Path:
        return self.session_root / "request.json"

    @property
    def response_path(self) -> Path:
        return self.session_root / "response.json"

    @property
    def snapshot_path(self) -> Path:
        return self.session_root / "snapshot.json"

    @property
    def result_path(self) -> Path:
        return self.session_root / "result.json"

    @property
    def run_log_path(self) -> Path:
        return self.session_root / "run.log"

    @property
    def cancel_path(self) -> Path:
        return self.session_root / "cancel.request"

    @property
    def home_path(self) -> Path:
        return self.session_root / "home"
