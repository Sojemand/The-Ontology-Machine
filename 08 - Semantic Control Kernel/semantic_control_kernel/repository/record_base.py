from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, ClassVar, Mapping

from semantic_control_kernel.repository.errors import StateCorruptionError


def _copy(payload: Mapping[str, Any]) -> dict[str, Any]:
    return deepcopy(dict(payload))


@dataclass(frozen=True)
class RepositoryRecord:
    payload: dict[str, Any] = field(default_factory=dict)

    SCHEMA_VERSION: ClassVar[str] = ""
    REQUIRED_FIELDS: ClassVar[tuple[str, ...]] = ("schema_version",)
    OPTIONAL_FIELDS: ClassVar[tuple[str, ...]] = ()
    ENUM_FIELDS: ClassVar[dict[str, tuple[str, ...]]] = {}

    def __post_init__(self) -> None:
        copied = _copy(self.payload)
        if self.SCHEMA_VERSION and "schema_version" not in copied:
            copied["schema_version"] = self.SCHEMA_VERSION
        self._validate(copied)
        object.__setattr__(self, "payload", copied)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RepositoryRecord":
        return cls(_copy(payload))

    def to_dict(self) -> dict[str, Any]:
        return _copy({**self.payload, "schema_version": self.SCHEMA_VERSION})

    def with_updates(self, **updates: Any) -> "RepositoryRecord":
        payload = self.to_dict()
        payload.update(updates)
        return type(self)(payload)

    def get(self, key: str, default: Any = None) -> Any:
        return self.payload.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self.payload[key]

    def __getattr__(self, key: str) -> Any:
        if key in self.payload:
            return self.payload[key]
        raise AttributeError(key)

    @classmethod
    def _validate(cls, payload: Mapping[str, Any]) -> None:
        missing = [field_name for field_name in cls.REQUIRED_FIELDS if field_name not in payload]
        if missing:
            raise StateCorruptionError(f"{cls.SCHEMA_VERSION} missing required field(s): {', '.join(missing)}")
        if cls.SCHEMA_VERSION and payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise StateCorruptionError(f"Expected {cls.SCHEMA_VERSION}, got {payload.get('schema_version')!r}")
        allowed = set(cls.REQUIRED_FIELDS) | set(cls.OPTIONAL_FIELDS)
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise StateCorruptionError(f"{cls.SCHEMA_VERSION} has unknown field(s): {', '.join(unknown)}")
        for field_name, values in cls.ENUM_FIELDS.items():
            if field_name in payload and payload[field_name] not in values:
                raise StateCorruptionError(
                    f"{cls.SCHEMA_VERSION}.{field_name} must be one of {values}, got {payload[field_name]!r}"
                )
