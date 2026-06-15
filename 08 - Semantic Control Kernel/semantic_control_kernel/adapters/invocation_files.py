from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.atomic_json import AtomicJsonStore, atomic_write_text, stable_json_dumps
from semantic_control_kernel.repository.hard_cap_limits import (
    RAW_ADAPTER_CALL_STRUCTURED_FILE_BYTES_HARD_CAP,
    RAW_ADAPTER_CALL_TEXT_FILE_BYTES_HARD_CAP,
)
from semantic_control_kernel.repository.ids import require_state_id
from semantic_control_kernel.repository.paths import StatePaths


@dataclass(frozen=True)
class AdapterCallFiles:
    call_dir: Path
    request_path: Path
    raw_response_path: Path
    raw_response_work_path: Path
    response_path: Path
    result_path: Path
    stdout_path: Path
    stderr_path: Path
    diagnostics_path: Path


def adapter_call_files(paths: StatePaths, call_id: str) -> AdapterCallFiles:
    call_id = require_state_id("adapter_call_id", call_id)
    call_dir = paths.adapter_calls_dir / call_id
    return AdapterCallFiles(
        call_dir=call_dir,
        request_path=call_dir / "request.json",
        raw_response_path=call_dir / "owner_response.raw.json",
        raw_response_work_path=paths.tmp_dir / f".{call_id}.owner_response.raw.json.tmp",
        response_path=call_dir / "response.json",
        result_path=call_dir / "result.json",
        stdout_path=call_dir / "stdout.txt",
        stderr_path=call_dir / "stderr.txt",
        diagnostics_path=call_dir / "diagnostics.json",
    )


def relative_ref(state_root: Path, path: Path) -> str:
    try:
        return path.relative_to(state_root).as_posix()
    except ValueError:
        return str(path)


def write_json(json_store: AtomicJsonStore, path: Path, payload: Mapping[str, Any]) -> None:
    json_store.write_json(path, _bounded_json_payload(path, payload), file_lock=False)


def write_text(path: Path, text: str) -> None:
    atomic_write_text(path, _bounded_text(text, RAW_ADAPTER_CALL_TEXT_FILE_BYTES_HARD_CAP))


def _bounded_json_payload(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(payload)
    size = len(stable_json_dumps(copied).encode("utf-8"))
    if size <= RAW_ADAPTER_CALL_STRUCTURED_FILE_BYTES_HARD_CAP:
        return copied
    return {
        "schema_version": "adapter.debug_file_truncated.v1",
        "adapter_debug_file": path.name,
        "original_size_bytes": size,
        "size_limit_bytes": RAW_ADAPTER_CALL_STRUCTURED_FILE_BYTES_HARD_CAP,
        "truncated": True,
        "diagnostics": [{"code": "adapter_debug_file_size_limit_exceeded"}],
    }


def _bounded_text(text: str, max_bytes: int) -> str:
    data = text.encode("utf-8")
    if len(data) <= max_bytes:
        return text
    marker = f"\n[truncated: original_size_bytes={len(data)} size_limit_bytes={max_bytes}]\n"
    marker_data = marker.encode("utf-8")
    keep = max(0, max_bytes - len(marker_data))
    return data[:keep].decode("utf-8", errors="ignore") + marker
