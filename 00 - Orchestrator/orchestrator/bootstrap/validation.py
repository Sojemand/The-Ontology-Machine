"""Hard bootstrap validation for manifests, paths and runtime contracts."""

from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from .debug_surface import coerce_debug_surface
from .exceptions import ModuleRegistryError
from .types import ExternalDependencySpec, ModuleManifestSpec, SUPPORTED_CONTRACT_VERSION


def _label(module_root: Path, *, module_key: str = "", manifest_path: Path | None = None) -> str:
    if module_key and manifest_path is not None:
        return f"{module_key}: {manifest_path}"
    return str(manifest_path or module_root)


def resolve_runtime_dir(
    module_root: Path,
    raw_runtime_dir: Any,
    *,
    module_key: str = "",
    manifest_path: Path | None = None,
) -> Path:
    runtime_dir = str(raw_runtime_dir or "runtime/python").strip() or "runtime/python"
    label = _label(module_root, module_key=module_key, manifest_path=manifest_path)
    windows_path = PureWindowsPath(runtime_dir)
    posix_path = PurePosixPath(runtime_dir.replace("\\", "/"))
    if windows_path.is_absolute() or windows_path.drive or windows_path.root or posix_path.is_absolute():
        raise ModuleRegistryError(f"runtime_dir must be relative to the module for {label}")

    parts: list[str] = []
    for part in runtime_dir.replace("\\", "/").split("/"):
        normalized = part.strip()
        if not normalized or normalized == ".":
            continue
        if normalized == ".." or ":" in normalized:
            raise ModuleRegistryError(f"runtime_dir is invalid for {label}: {runtime_dir}")
        parts.append(normalized)

    candidate = module_root.joinpath(*(parts or ["runtime", "python"])).resolve()
    try:
        candidate.relative_to(module_root.resolve())
    except ValueError as exc:
        raise ModuleRegistryError(
            f"runtime_dir is outside the module folder for {label}: {runtime_dir}"
        ) from exc
    return candidate


def _coerce_contract_version(raw: Any, module_key: str, manifest_path: Path) -> int:
    try:
        version = int(raw)
    except (TypeError, ValueError) as exc:
        raise ModuleRegistryError(
            f"Invalid contract_version for {module_key}: {manifest_path}"
        ) from exc
    if version != SUPPORTED_CONTRACT_VERSION:
        raise ModuleRegistryError(
            f"Unsupported contract_version for {module_key}: {version} "
            f"(expected {SUPPORTED_CONTRACT_VERSION})"
        )
    return version


def _coerce_actions(raw_actions: Any, module_key: str, manifest_path: Path) -> tuple[str, ...]:
    if not isinstance(raw_actions, list):
        raise ModuleRegistryError(f"actions must be an array for {module_key}: {manifest_path}")
    actions = tuple(str(item).strip() for item in raw_actions if str(item).strip())
    if not actions:
        raise ModuleRegistryError(f"No actions declared for {module_key}: {manifest_path}")
    return actions


def _coerce_external_dependencies(
    raw_dependencies: Any,
    module_key: str,
    manifest_path: Path,
) -> tuple[ExternalDependencySpec, ...]:
    if not isinstance(raw_dependencies, list):
        raise ModuleRegistryError(
            f"external_dependencies must be an array for {module_key}: {manifest_path}"
        )
    dependencies: list[ExternalDependencySpec] = []
    for index, item in enumerate(raw_dependencies):
        if not isinstance(item, dict):
            raise ModuleRegistryError(
                f"external_dependencies[{index}] is invalid for {module_key}: {manifest_path}"
            )
        name = str(item.get("name", "")).strip()
        if not name:
            raise ModuleRegistryError(
                f"external_dependencies[{index}] is missing a name for {module_key}: {manifest_path}"
            )
        dependencies.append(
            ExternalDependencySpec(
                name=name,
                kind=str(item.get("kind", "service")).strip() or "service",
                required=bool(item.get("required", True)),
                detail=str(item.get("detail", "")).strip(),
            )
        )
    return tuple(dependencies)


def coerce_manifest_spec(
    module_root: Path,
    manifest: dict[str, Any],
    *,
    expected_module_key: str = "",
    manifest_path: Path,
) -> ModuleManifestSpec:
    declared_key = str(manifest.get("module_key", "")).strip()
    if expected_module_key and declared_key and declared_key != expected_module_key:
        raise ModuleRegistryError(
            f"module_key mismatch for {manifest_path}: {declared_key} != {expected_module_key}"
        )
    module_key = expected_module_key or declared_key or module_root.name
    contract_module = str(manifest.get("contract_module", "")).strip()
    if not contract_module:
        raise ModuleRegistryError(f"contract_module is missing for {module_key}: {manifest_path}")
    return ModuleManifestSpec(
        key=module_key,
        display_name=str(manifest.get("display_name") or module_key),
        contract_module=contract_module,
        runtime_dir=resolve_runtime_dir(
            module_root,
            manifest.get("runtime_dir", "runtime/python"),
            module_key=module_key,
            manifest_path=manifest_path,
        ),
        manifest_path=manifest_path,
        contract_version=_coerce_contract_version(
            manifest.get("contract_version", SUPPORTED_CONTRACT_VERSION),
            module_key,
            manifest_path,
        ),
        actions=_coerce_actions(manifest.get("actions", []), module_key, manifest_path),
        external_dependencies=_coerce_external_dependencies(
            manifest.get("external_dependencies", []),
            module_key,
            manifest_path,
        ),
        debug_surface=coerce_debug_surface(
            manifest.get("debug_surface"),
            module_key=module_key,
            manifest_path=manifest_path,
        ),
    )
