from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, ClassVar, Mapping


ADAPTER_CALL_REQUEST_SCHEMA_VERSION = "adapter.call_request.v1"
ADAPTER_CALL_RESPONSE_SCHEMA_VERSION = "adapter.call_response.v1"
ADAPTER_CALL_RESULT_SCHEMA_VERSION = "adapter.call_result.v1"
ADAPTER_MISSING_CAPABILITY_BLOCKER_SCHEMA_VERSION = "adapter.missing_capability_blocker.v1"

ADAPTER_RESULT_STATUSES: tuple[str, ...] = (
    "ok",
    "owner_error",
    "timeout",
    "cancelled",
    "invalid_owner_response",
    "missing_capability",
    "target_identity_changed",
    "target_identity_unproven",
    "blocked_by_kernel_precondition",
)

CAPABILITY_STATUSES: tuple[str, ...] = (
    "implemented_in_pipeline",
    "kernel_composition_over_existing_primitives",
    "deferred_to_phase_19",
    "kernel_internal_no_pipeline_adapter",
    "legacy_mcp_false_friend_hidden",
    "kernel_continuation_scoped",
)


def _copy_mapping(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return deepcopy(dict(payload or {}))


@dataclass(frozen=True)
class LocalAdapterContract:
    payload: dict[str, Any] = field(default_factory=dict)

    SCHEMA_VERSION: ClassVar[str] = ""

    def __post_init__(self) -> None:
        copied = _copy_mapping(self.payload)
        copied.setdefault("schema_version", self.SCHEMA_VERSION)
        object.__setattr__(self, "payload", copied)

    @property
    def schema_version(self) -> str:
        value = self.payload.get("schema_version")
        return value if isinstance(value, str) else self.SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        copied = _copy_mapping(self.payload)
        copied["schema_version"] = self.SCHEMA_VERSION
        return copied


@dataclass(frozen=True)
class AdapterCallRequest(LocalAdapterContract):
    SCHEMA_VERSION: ClassVar[str] = ADAPTER_CALL_REQUEST_SCHEMA_VERSION


@dataclass(frozen=True)
class AdapterCallResponse(LocalAdapterContract):
    SCHEMA_VERSION: ClassVar[str] = ADAPTER_CALL_RESPONSE_SCHEMA_VERSION


@dataclass(frozen=True)
class AdapterCallResult(LocalAdapterContract):
    SCHEMA_VERSION: ClassVar[str] = ADAPTER_CALL_RESULT_SCHEMA_VERSION

    @property
    def status(self) -> str:
        value = self.payload.get("status")
        return value if isinstance(value, str) else "invalid_owner_response"

    @property
    def adapter_call_id(self) -> str:
        value = self.payload.get("adapter_call_id")
        return value if isinstance(value, str) else ""

    @property
    def capability_status(self) -> str:
        value = self.payload.get("capability_status")
        return value if isinstance(value, str) else ""


@dataclass(frozen=True)
class MissingCapabilityBlocker(LocalAdapterContract):
    SCHEMA_VERSION: ClassVar[str] = ADAPTER_MISSING_CAPABILITY_BLOCKER_SCHEMA_VERSION

    @property
    def kernel_function(self) -> str:
        value = self.payload.get("kernel_function")
        return value if isinstance(value, str) else ""

    @property
    def required_capability(self) -> str:
        value = self.payload.get("required_capability")
        return value if isinstance(value, str) else ""


from semantic_control_kernel.types.adapter_result_factories import (  # noqa: E402
    make_call_request,
    make_call_response,
    make_call_result,
    make_missing_capability_blocker,
)
