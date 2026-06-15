from __future__ import annotations

from edit_suite.registry.types import ModuleReadinessEntry


def entry(slot_name: str, readiness: str, *, diagnostic: str = "") -> ModuleReadinessEntry:
    blockers = (readiness,) if readiness != "ready" else ()
    return ModuleReadinessEntry(
        slot_name=slot_name,
        display_name=slot_name,
        module_root=f"C:/{slot_name}",
        module_key=slot_name.lower().replace(" ", "_"),
        readiness=readiness,
        blockers=blockers,
        manifest_path="manifest",
        manifest_present=readiness != "missing_manifest",
        edit_contract_path="",
        runtime_available=True,
        diagnostic=diagnostic,
    )
