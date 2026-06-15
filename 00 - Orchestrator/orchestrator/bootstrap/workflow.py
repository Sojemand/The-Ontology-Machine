"""Bootstrap workflow for registry loading and startup prerequisites."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import adapter, validation
from .exceptions import ModuleRegistryError, StartupPrerequisiteError
from .types import ModuleManifestSpec, ModuleRuntimeSpec


def _coerce_raw_manifest(
    module_root: Path,
    manifest: dict[str, Any] | None,
) -> tuple[dict[str, Any], Path]:
    manifest_file = adapter.manifest_path(module_root)
    if manifest is None:
        return adapter.load_json_object(manifest_file, label="module-manifest.json"), manifest_file
    if not isinstance(manifest, dict):
        raise ModuleRegistryError(f"module-manifest.json must be a JSON object: {manifest_file}")
    return manifest, manifest_file


def _load_manifest_spec(module_key: str, module_root: Path) -> ModuleManifestSpec:
    manifest_file = adapter.manifest_path(module_root)
    manifest = adapter.load_json_object(manifest_file, label="module-manifest.json")
    return validation.coerce_manifest_spec(
        module_root,
        manifest,
        expected_module_key=module_key,
        manifest_path=manifest_file,
    )


def _resolve_python_executable(module_root: Path, runtime_dir: Path) -> Path:
    candidates = adapter.bundled_python_candidates(module_root, runtime_dir)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _build_runtime_spec(module_key: str, module_root: Path) -> ModuleRuntimeSpec:
    if not module_root.exists():
        raise ModuleRegistryError(f"Module path is missing for {module_key}: {module_root}")
    manifest_spec = _load_manifest_spec(module_key, module_root)
    if not manifest_spec.runtime_dir.exists():
        raise ModuleRegistryError(
            f"Runtime directory is missing for {module_key}: {manifest_spec.runtime_dir}"
        )
    python_executable = _resolve_python_executable(module_root, manifest_spec.runtime_dir)
    if not python_executable.exists():
        raise ModuleRegistryError(f"Bundled runtime is missing for {module_key}: {python_executable}")
    return ModuleRuntimeSpec(
        key=manifest_spec.key,
        display_name=manifest_spec.display_name,
        module_root=module_root,
        contract_module=manifest_spec.contract_module,
        runtime_dir=manifest_spec.runtime_dir,
        python_executable=python_executable,
        manifest_path=manifest_spec.manifest_path,
        contract_version=manifest_spec.contract_version,
        actions=manifest_spec.actions,
        external_dependencies=manifest_spec.external_dependencies,
        debug_surface=manifest_spec.debug_surface,
    )


def resolve_bundled_python(module_root: Path, manifest: dict[str, Any] | None = None) -> Path:
    raw_manifest, manifest_file = _coerce_raw_manifest(module_root, manifest)
    runtime_dir = validation.resolve_runtime_dir(
        module_root,
        raw_manifest.get("runtime_dir", "runtime/python"),
        manifest_path=manifest_file,
    )
    return _resolve_python_executable(module_root, runtime_dir)


def load_module_registry(registry_path: Path | None = None) -> dict[str, ModuleRuntimeSpec]:
    resolved_registry_path = adapter.resolve_registry_path(registry_path)
    payload = adapter.load_json_object(resolved_registry_path, label="module-registry.json")
    raw_modules = payload.get("modules")
    if not isinstance(raw_modules, dict) or not raw_modules:
        raise ModuleRegistryError(f"module-registry.json contains no modules: {resolved_registry_path}")
    specs: dict[str, ModuleRuntimeSpec] = {}
    for module_key, raw_entry in raw_modules.items():
        normalized_key = str(module_key).strip()
        if not normalized_key:
            raise ModuleRegistryError(f"Empty module_key in {resolved_registry_path}")
        module_root = adapter.resolve_module_root(resolved_registry_path, raw_entry)
        specs[normalized_key] = _build_runtime_spec(normalized_key, module_root)
    return specs


def resolve_module_runtime(
    module_key: str,
    *,
    registry_path: Path | None = None,
    required_actions: tuple[str, ...] = (),
) -> ModuleRuntimeSpec:
    try:
        spec = load_module_registry(registry_path)[module_key]
    except KeyError as exc:
        raise ModuleRegistryError(f"Unknown module in registry: {module_key}") from exc
    spec.require_actions(*required_actions)
    return spec


def ensure_startup_prerequisites(registry_path: Path | None = None) -> dict[str, ModuleRuntimeSpec]:
    resolved_registry_path = adapter.resolve_registry_path(registry_path)
    try:
        specs = load_module_registry(resolved_registry_path)
    except ModuleRegistryError as exc:
        raise StartupPrerequisiteError(
            "The Orchestrator requires the neighboring vision modules listed in "
            f"{resolved_registry_path.name} in the same pipeline root. Current error: {exc}"
        ) from exc
    try:
        adapter.require_python_module("customtkinter")
    except ModuleNotFoundError as exc:
        if exc.name != "customtkinter":
            raise
        raise StartupPrerequisiteError(
            "The bundled runtime is incomplete: customtkinter is missing. "
            "Run build-runtime.bat again."
        ) from exc
    return specs
