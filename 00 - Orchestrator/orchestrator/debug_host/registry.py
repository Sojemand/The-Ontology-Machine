"""Central registry for generic debug-host descriptors and plans."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..bootstrap import ModuleRuntimeSpec, adapter as bootstrap_adapter, load_module_registry
from ..integrations import stage_name_for_module
from .types import DebugDescriptor, DebugPlan, DebugStep

_ALLOWED_CONTROLS = {
    "mode",
    "filters",
    "worker_count",
    "hash_tools",
    "raw_evidence",
    "check_toggles",
    "persist_page_images",
}
_HOME_ENV_VARS = {
    "optimizer": "OPTIMIZER_HOME",
    "interpreter": "INTERPRETER_HOME",
    "validator": "VALIDATOR_VISION_HOME",
}
_INTERPRETER_PREREQUISITES = {
    "interpreter": "optimizer",
}
_CATALOGS: dict[str, "_DebugCatalog"] = {}


@dataclass
class _DebugCatalog:
    specs: dict[str, ModuleRuntimeSpec]
    descriptors: dict[str, DebugDescriptor]
    plans: dict[tuple[str, str], DebugPlan] = field(default_factory=dict)


def available_descriptors(*, registry_path=None) -> dict[str, DebugDescriptor]:
    return dict(_catalog(registry_path).descriptors)


def descriptor_for(module_key: str, *, registry_path=None) -> DebugDescriptor:
    spec = module_runtime(module_key, registry_path=registry_path)
    descriptor = _catalog(registry_path).descriptors.get(spec.key)
    if descriptor is None:
        raise ValueError(f"debug_surface is missing for {module_key}: {spec.manifest_path}")
    return descriptor


def plan_for(module_key: str, mode: str, *, registry_path=None) -> DebugPlan:
    normalized = str(mode or "").strip().lower()
    catalog = _catalog(registry_path)
    cache_key = (module_key, normalized)
    if cache_key not in catalog.plans:
        catalog.plans[cache_key] = _build_plan(descriptor_for(module_key, registry_path=registry_path), normalized)
    return catalog.plans[cache_key]


def module_runtime(module_key: str, *, registry_path=None, required_actions: tuple[str, ...] = ()) -> ModuleRuntimeSpec:
    from ..bootstrap.exceptions import ModuleRegistryError

    spec = _catalog(registry_path).specs.get(module_key)
    if spec is None:
        raise ModuleRegistryError(f"Unknown module in registry: {module_key}")
    spec.require_actions(*required_actions)
    return spec


def session_home_env(module_key: str) -> str:
    return _HOME_ENV_VARS.get(module_key, "")


def _catalog(registry_path=None) -> _DebugCatalog:
    key = str(bootstrap_adapter.resolve_registry_path(registry_path))
    catalog = _CATALOGS.get(key)
    if catalog is not None:
        return catalog
    specs = load_module_registry(registry_path)
    catalog = _DebugCatalog(specs=specs, descriptors=_build_descriptors(specs))
    _CATALOGS[key] = catalog
    return catalog


def _build_descriptors(specs: dict[str, ModuleRuntimeSpec]) -> dict[str, DebugDescriptor]:
    descriptors: dict[str, DebugDescriptor] = {}
    for module_key, spec in specs.items():
        surface = spec.debug_surface
        if surface is None:
            continue
        unknown = sorted(set(surface.controls).difference(_ALLOWED_CONTROLS))
        if unknown:
            joined = ", ".join(unknown)
            raise ValueError(f"Unknown debug_surface.controls for {module_key}: {joined}")
        descriptors[module_key] = DebugDescriptor(
            module_key=spec.key,
            display_name=spec.display_name,
            stage_role=stage_name_for_module(spec.key),
            supports_batch=surface.supports_batch,
            supports_single=surface.supports_single,
            supports_scan=surface.supports_scan,
            input_source=surface.input_source,
            output_source=surface.output_source,
            controls=surface.controls,
            artifacts=surface.artifacts,
        )
    return descriptors


def _build_plan(descriptor: DebugDescriptor, mode: str) -> DebugPlan:
    prerequisite = _INTERPRETER_PREREQUISITES.get(descriptor.module_key)
    if prerequisite:
        if mode == "scan" and descriptor.supports_scan:
            return DebugPlan("scan", (DebugStep.module(prerequisite, "scan_debug_input"),))
        if mode in {"single", "batch"} and getattr(descriptor, f"supports_{mode}", False):
            return DebugPlan(
                mode,
                (
                    DebugStep.module(prerequisite, "debug_run"),
                    DebugStep.host("request_enrichment"),
                    DebugStep.module(descriptor.module_key, "debug_run"),
                ),
            )
    if mode == "scan" and descriptor.supports_scan:
        return DebugPlan("scan", (DebugStep.module(descriptor.module_key, "scan_debug_input"),))
    if mode == "single" and descriptor.supports_single:
        return DebugPlan("single", (DebugStep.module(descriptor.module_key, "debug_run"),))
    if mode == "batch" and descriptor.supports_batch:
        return DebugPlan("batch", (DebugStep.module(descriptor.module_key, "debug_run"),))
    raise ValueError(f"Mode is not supported: {descriptor.module_key}/{mode}")
