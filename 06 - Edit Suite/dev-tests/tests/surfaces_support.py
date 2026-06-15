from __future__ import annotations

import importlib

from edit_suite.registry.types import ModuleReadinessEntry

bundle_workflow = importlib.import_module("edit_suite.surfaces.load_bundle")


def entry() -> ModuleReadinessEntry:
    return ModuleReadinessEntry(
        slot_name="01 - Optimizer",
        display_name="Optimizer",
        module_root="C:/ImageOptimizer",
        module_key="optimizer",
        readiness="ready",
        blockers=(),
        manifest_path="manifest",
        manifest_present=True,
        edit_contract_path="ingestion_layer_vision/edit_contract",
        runtime_available=True,
    )
