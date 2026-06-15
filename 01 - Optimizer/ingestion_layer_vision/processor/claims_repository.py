"""Claiming and output-directory persistence helpers for the processor."""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

from .claim_process import pid_claim_is_active

logger = logging.getLogger(__name__)

_RUN_LOCK_NAME = ".ingestor_active.lock"
_RUNS_DIR_NAME = "runs"
_OUTPUT_CLAIM_SUFFIX = ".claim"


def prepare_output_dir(processor, requested_output: Path) -> Path:
    requested_output = Path(requested_output)
    requested_output.mkdir(parents=True, exist_ok=True)
    effective_output = processor._try_claim_output_dir(requested_output) or processor._claim_child_output_dir(requested_output)
    processor._set_output_dir(effective_output)
    return effective_output


def set_output_dir(processor, output_dir: Path) -> None:
    processor._output_dir = Path(output_dir)
    processor._extracts_dir = processor._output_dir / "raw_extracts"
    processor._report.output_directory = str(processor._output_dir)


def try_claim_output_dir(processor, output_dir: Path) -> Path | None:
    lock_path = output_dir / _RUN_LOCK_NAME
    for _ in range(2):
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if _clear_stale_run_lock(lock_path):
                continue
            return None
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(_claim_payload())
        processor._run_lock_path = lock_path
        return output_dir
    return None


def claim_child_output_dir(processor, base_output: Path) -> Path:
    runs_dir = base_output / _RUNS_DIR_NAME
    runs_dir.mkdir(parents=True, exist_ok=True)
    for _ in range(32):
        run_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        candidate = runs_dir / run_name
        try:
            candidate.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        claimed = processor._try_claim_output_dir(candidate)
        if claimed:
            return claimed
    raise RuntimeError(f"Kein kollisionsfreies Run-Output unter {runs_dir} verfuegbar")


def release_output_claim(processor) -> None:
    if not processor._run_lock_path:
        return
    try:
        processor._run_lock_path.unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("Run-Lock konnte nicht entfernt werden: %s", exc)
    finally:
        processor._run_lock_path = None


def output_claim_path(output_path: Path) -> Path:
    return output_path.with_name(f"{output_path.name}{_OUTPUT_CLAIM_SUFFIX}")


def try_claim_output_candidate(processor, output_path: Path) -> Path | None:
    claim_path = processor._output_claim_path(output_path)
    try:
        fd = os.open(str(claim_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return None
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(_claim_payload())
    return claim_path


def _claim_payload() -> str:
    return json.dumps({"pid": os.getpid(), "created_at": datetime.now().isoformat()}, ensure_ascii=False)


def _clear_stale_run_lock(lock_path: Path) -> bool:
    payload = _load_lock_payload(lock_path)
    if payload is None:
        return False
    pid = int(payload["pid"])
    if pid_claim_is_active(pid, payload.get("created_at")):
        return False
    try:
        lock_path.unlink()
    except FileNotFoundError:
        logger.info("Verwaistes Run-Lock wurde bereits entfernt: %s", lock_path)
        return True
    except OSError as exc:
        logger.warning("Verwaistes Run-Lock konnte nicht entfernt werden (%s): %s", lock_path, exc)
        return False
    logger.warning("Verwaistes Run-Lock entfernt: %s (pid=%s)", lock_path, pid)
    return True


def _load_lock_payload(lock_path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    pid = payload.get("pid")
    if not isinstance(pid, int) or pid <= 0:
        return None
    return payload
