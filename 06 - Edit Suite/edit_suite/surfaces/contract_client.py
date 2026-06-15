"""Path-stable surface for owner-provided contract calls."""
from __future__ import annotations

from pathlib import Path

from ..contract_runtime import invoke_owner_contract
from ..registry.types import ModuleReadinessEntry


def invoke_contract(entry: ModuleReadinessEntry, state_root: Path, payload: dict) -> dict:
    return invoke_owner_contract(
        module_root=Path(entry.module_root),
        contract_path=entry.edit_contract_path,
        state_root=state_root,
        payload=payload,
    )
