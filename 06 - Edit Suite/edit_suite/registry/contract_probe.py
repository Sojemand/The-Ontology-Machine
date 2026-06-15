"""Cheap contract bootstrap probes for registry readiness."""
from __future__ import annotations

from pathlib import Path

from ..contract_runtime import invoke_owner_contract


def probe_contract(module_root: Path, contract_path: str, *, state_root: Path) -> str:
    try:
        response = invoke_owner_contract(
            module_root=module_root,
            contract_path=contract_path,
            state_root=state_root,
            payload={"action": "describe_surfaces"},
        )
    except Exception as exc:
        return str(exc)
    if str(response.get("status") or "") == "ok":
        return ""
    return str(response.get("reason") or response.get("message") or "Contract error")
