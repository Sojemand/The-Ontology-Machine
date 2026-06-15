"""Central registry for sibling-module control metadata."""

from __future__ import annotations

from dataclasses import dataclass

from .. import policy_store


@dataclass(frozen=True)
class ModuleRegistryEntry:
    module_key: str
    display_name: str
    stage_role: str
    required_actions: tuple[str, ...]


@dataclass(frozen=True)
class ContractOperation:
    name: str
    module_key: str
    action: str
    timeout: int


def pipeline_stage_names() -> tuple[str, ...]:
    return policy_store.pipeline_stage_names()


def default_module_keys() -> tuple[str, ...]:
    return policy_store.default_module_keys()


def healthcheck_timeout_seconds() -> int:
    return policy_store.healthcheck_timeout_seconds()


def module_entry(module_key: str) -> ModuleRegistryEntry:
    payload = policy_store.module_policy(module_key)
    return ModuleRegistryEntry(
        module_key=module_key,
        display_name=str(payload["display_name"]),
        stage_role=str(payload["stage_role"]),
        required_actions=tuple(str(action) for action in payload["required_actions"]),
    )


def operation_entry(operation_name: str) -> ContractOperation:
    return ContractOperation(
        name=operation_name,
        module_key=_first_module_for_action(operation_name),
        action=operation_name,
        timeout=policy_store.operation_timeout_seconds(operation_name),
    )


def required_actions_by_module() -> dict[str, tuple[str, ...]]:
    return policy_store.required_actions_by_module_policy()


def stage_name_for_module(module_key: str) -> str:
    return module_entry(module_key).stage_role


def _first_module_for_action(operation_name: str) -> str:
    for module_key, actions in required_actions_by_module().items():
        if operation_name in actions:
            return module_key
    raise KeyError(operation_name)


def __getattr__(name: str):
    dynamic = {
        "PIPELINE_STAGE_NAMES": pipeline_stage_names,
        "DEFAULT_MODULE_KEYS": default_module_keys,
        "HEALTHCHECK_TIMEOUT_SECONDS": healthcheck_timeout_seconds,
    }
    if name in dynamic:
        return dynamic[name]()
    raise AttributeError(name)
