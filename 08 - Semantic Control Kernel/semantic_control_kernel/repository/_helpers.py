from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, TypeVar

from semantic_control_kernel.repository.errors import TargetIdentityMismatchError
from semantic_control_kernel.repository.paths import StatePaths, path_hash, stable_hash
from semantic_control_kernel.types.base import KernelContract
from semantic_control_kernel.types.identity import TargetIdentity
from semantic_control_kernel.validation.contract_validation import serialize_contract


ContractT = TypeVar("ContractT", bound=KernelContract)


def payload_from_mapping(value: Mapping[str, Any] | TargetIdentity) -> dict[str, Any]:
    if isinstance(value, TargetIdentity):
        return value.to_dict()
    return deepcopy(dict(value))


def target_identity_hash(target_identity: Mapping[str, Any] | TargetIdentity) -> str:
    payload = payload_from_mapping(target_identity)
    for key in ("target_hash", "database_path_hash", "artifact_root_path_hash"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    for key in ("database_path", "artifact_root_path", "target_path"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return path_hash(value)
    return stable_hash(json.dumps(payload, sort_keys=True))


def target_identity_scope(target_identity: Mapping[str, Any] | TargetIdentity) -> str:
    payload = payload_from_mapping(target_identity)
    value = payload.get("lock_scope") or payload.get("target_scope") or payload.get("kind") or "target"
    return str(value)


def target_identity_index_key(target_identity: Mapping[str, Any] | TargetIdentity) -> str:
    payload = payload_from_mapping(target_identity)
    return payload.get("target_hash") or payload.get("database_path_hash") or payload.get("artifact_root_path_hash") or target_identity_hash(payload)


def require_same_identity(expected: Mapping[str, Any], actual: Mapping[str, Any], label: str) -> None:
    if deepcopy(dict(expected)) != deepcopy(dict(actual)):
        raise TargetIdentityMismatchError(f"{label} identity mismatch.")


def contract_payload(contract: ContractT, expected_type: type[ContractT]) -> dict[str, Any]:
    if not isinstance(contract, expected_type):
        raise TypeError(f"Expected {expected_type.__name__}, got {type(contract).__name__}.")
    return serialize_contract(contract)


def parse_contract_payload(payload: Mapping[str, Any], contract_type: type[ContractT]) -> ContractT:
    return contract_type.from_dict(payload)


def relative_ref(paths: StatePaths, path: Path) -> dict[str, str]:
    return {"state_path": paths.relative_to_state_root(path)}
