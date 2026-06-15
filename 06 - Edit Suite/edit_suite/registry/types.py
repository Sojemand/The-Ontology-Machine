"""Datatypes for discovery and readiness."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModuleReadinessEntry:
    slot_name: str
    display_name: str
    module_root: str
    module_key: str
    readiness: str
    blockers: tuple[str, ...]
    manifest_path: str
    manifest_present: bool
    edit_contract_path: str
    runtime_available: bool
    diagnostic: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_name": self.slot_name,
            "display_name": self.display_name,
            "module_root": self.module_root,
            "module_key": self.module_key,
            "readiness": self.readiness,
            "blockers": list(self.blockers),
            "manifest_path": self.manifest_path,
            "manifest_present": self.manifest_present,
            "edit_contract_path": self.edit_contract_path,
            "runtime_available": self.runtime_available,
            "diagnostic": self.diagnostic,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ModuleReadinessEntry":
        return cls(
            slot_name=str(payload.get("slot_name") or ""),
            display_name=str(payload.get("display_name") or ""),
            module_root=str(payload.get("module_root") or ""),
            module_key=str(payload.get("module_key") or ""),
            readiness=str(payload.get("readiness") or "missing_manifest"),
            blockers=tuple(str(item) for item in payload.get("blockers", [])),
            manifest_path=str(payload.get("manifest_path") or ""),
            manifest_present=bool(payload.get("manifest_present")),
            edit_contract_path=str(payload.get("edit_contract_path") or ""),
            runtime_available=bool(payload.get("runtime_available")),
            diagnostic=str(payload.get("diagnostic") or ""),
        )


@dataclass(frozen=True)
class RegistrySnapshot:
    generated_at: str
    source: str
    stale: bool
    message: str
    entries: tuple[ModuleReadinessEntry, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "source": self.source,
            "stale": self.stale,
            "message": self.message,
            "entries": [entry.to_dict() for entry in self.entries],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RegistrySnapshot":
        return cls(
            generated_at=str(payload.get("generated_at") or ""),
            source=str(payload.get("source") or "cache"),
            stale=bool(payload.get("stale")),
            message=str(payload.get("message") or ""),
            entries=tuple(ModuleReadinessEntry.from_dict(item) for item in payload.get("entries", [])),
        )
