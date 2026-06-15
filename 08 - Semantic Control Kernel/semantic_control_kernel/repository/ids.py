from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone

STATE_ID_MAX_LENGTH = 96
STATE_ID_RANDOM_HEX_LENGTH = 16
_STATE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


ID_PREFIXES: dict[str, str] = {
    "workflow_run_id": "wr",
    "state_snapshot_id": "ss",
    "confirmation_request_id": "cfq",
    "confirmation_receipt_id": "cfr",
    "interaction_request_id": "irq",
    "interaction_response_id": "irs",
    "frontend_event_id": "cfe",
    "operation_receipt_id": "opr",
    "recovery_receipt_id": "rcr",
    "lock_id": "lck",
    "recovery_id": "rcv",
    "analysis_run_id": "ana",
    "merge_run_id": "mrg",
    "pipeline_batch_id": "pbt",
    "progress_event_id": "pev",
    "mirror_event_id": "mev",
    "recovery_event_id": "rev",
    "support_bundle_id": "spt",
    "adapter_call_id": "adc",
    "background_continuation_id": "bgc",
    "trace_id": "trc",
    "llm_attempt_id": "lat",
    "diagnostic_id": "dia",
    "rebuild_run_id": "rbd",
    "reset_id": "rst",
}


def utc_compact_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def generate_id(identifier: str) -> str:
    prefix = ID_PREFIXES.get(identifier, identifier if identifier in set(ID_PREFIXES.values()) else "")
    if not prefix:
        raise ValueError(f"Unknown Kernel identifier prefix: {identifier}")
    return f"{prefix}_{secrets.token_hex(STATE_ID_RANDOM_HEX_LENGTH // 2)}"


def generate_prefixed_id(prefix: str) -> str:
    return generate_id(prefix)


def require_state_id(identifier: str, value: object) -> str:
    text = str(value or "")
    if len(text) > STATE_ID_MAX_LENGTH or not _STATE_ID_PATTERN.fullmatch(text):
        raise ValueError(
            f"{identifier} must be a non-empty Kernel state id using A-Z, a-z, 0-9, '_' or '-' "
            f"and at most {STATE_ID_MAX_LENGTH} characters."
        )
    return text
