"""Helper functions for subprocess workflow dispatch and healthchecks."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, TypeVar

from ..models.types import RuntimeSettingsState
from . import adapter, registry
from .types import ModuleHealthStatus

logger = logging.getLogger(__name__)
_T = TypeVar("_T")


def call_operation(
    modules: Any,
    operation_name: str,
    payload: dict[str, Any],
    *,
    parse: Callable[[dict[str, Any]], _T],
    on_error: Callable[[Exception], _T],
    log_message: str,
    module_key: str | None = None,
    env_overlay: dict[str, str] | None = None,
) -> _T:
    operation = registry.operation_entry(operation_name)
    target_module_key = module_key or operation.module_key
    try:
        data = adapter.invoke_contract(
            modules._runtime_specs[target_module_key],
            {"action": operation.action, **payload},
            timeout=operation.timeout,
            env_overlay=env_overlay,
        )
        return parse(data)
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        logger.exception(log_message)
        return on_error(exc)


def env_overlay_for(modules: Any, module_key: str) -> dict[str, str] | None:
    runtime_credentials = runtime_credentials_for(modules, module_key)
    if runtime_credentials is None:
        return None
    if not runtime_credentials.ready:
        raise RuntimeError(runtime_credentials.message or "; ".join(runtime_credentials.block_reasons))
    return runtime_credentials.env_overlay


def runtime_credentials_for(modules: Any, module_key: str, operation: str = ""):
    state_dir = getattr(modules, "_state_dir", None)
    if state_dir is None:
        return None
    from .. import credentials

    if module_key in {"interpreter", "normalizer", "optimizer", "corpus_builder"}:
        return credentials.resolve_runtime_credentials(state_dir, module_key, operation)
    return None


def health_runtime_credentials(modules: Any, module_key: str, *, required_dependencies: set[str] | None = None):
    if module_key in {"interpreter", "normalizer"}:
        return runtime_credentials_for(modules, module_key)
    if module_key == "optimizer" and required_dependencies and "optimizer_ocr" in required_dependencies:
        return runtime_credentials_for(modules, module_key)
    if module_key == "corpus_builder":
        return runtime_credentials_for(modules, module_key, "generate_embeddings")
    return None


def runtime_settings_for(modules: Any, module_key: str, operation: str = "") -> dict[str, Any] | None:
    runtime_settings = getattr(modules, "_runtime_settings", RuntimeSettingsState())
    return runtime_settings.runtime_settings_for(module_key, operation)


def required_runtime_settings_for(modules: Any, module_key: str, operation: str = "") -> dict[str, Any]:
    runtime_settings = runtime_settings_for(modules, module_key, operation)
    if runtime_settings is None:
        raise RuntimeError(f"Missing runtime_settings for {module_key}.")
    return runtime_settings


def healthcheck_statuses(
    modules: Any,
    *,
    module_keys: tuple[str, ...] | None = None,
    scope: str = "pipeline_run",
    required_dependencies_by_module: dict[str, tuple[str, ...]] | None = None,
    corpus_db_path: Path | None = None,
) -> list[ModuleHealthStatus]:
    results: list[ModuleHealthStatus] = []
    for module_key in module_keys or registry.default_module_keys():
        spec = modules._runtime_specs[module_key]
        required_dependencies = set(
            (required_dependencies_by_module or {}).get(module_key, ())
        )
        runtime_credentials = health_runtime_credentials(
            modules,
            module_key,
            required_dependencies=required_dependencies,
        )
        if runtime_credentials is not None and not runtime_credentials.ready and not runtime_credentials.warning_only:
            results.append(
                ModuleHealthStatus(
                    key=spec.key,
                    display_name=spec.display_name,
                    healthy=False,
                    message=runtime_credentials.message,
                )
            )
            continue
        try:
            data = adapter.invoke_contract(
                spec,
                healthcheck_payload(
                    modules,
                    module_key,
                    scope,
                    required_dependencies_by_module,
                    corpus_db_path,
                ),
                timeout=registry.healthcheck_timeout_seconds(),
                env_overlay=runtime_credentials.env_overlay if runtime_credentials is not None and runtime_credentials.ready else None,
            )
        except Exception as exc:
            results.append(ModuleHealthStatus(key=spec.key, display_name=spec.display_name, healthy=False, message=str(exc)))
            continue
        parsed = adapter.parse_health_status(spec, data)
        if runtime_credentials is not None and runtime_credentials.warning_only:
            parsed = downgrade_embeddings_warning(parsed, runtime_credentials.message)
        results.append(parsed)
    return results


def healthcheck_payload(
    modules: Any,
    module_key: str,
    scope: str,
    required_dependencies_by_module: dict[str, tuple[str, ...]] | None,
    corpus_db_path: Path | None = None,
) -> dict[str, Any]:
    runtime_settings = (
        required_runtime_settings_for(modules, "corpus_builder", "generate_embeddings")
        if module_key == "corpus_builder"
        else (
            required_runtime_settings_for(modules, module_key)
            if module_key in {"interpreter", "normalizer"}
            else None
        )
    )
    payload: dict[str, Any] = {"action": "healthcheck"}
    if runtime_settings is not None:
        payload["runtime_settings"] = runtime_settings
    if module_key in {"optimizer", "corpus_builder"}:
        payload["scope"] = scope
    if module_key == "corpus_builder" and corpus_db_path is not None:
        payload["corpus_db_path"] = str(corpus_db_path)
    if module_key == "optimizer" and required_dependencies_by_module and module_key in required_dependencies_by_module:
        payload["required_dependencies"] = list(required_dependencies_by_module[module_key])
    return payload


def downgrade_embeddings_warning(result: ModuleHealthStatus, detail: str) -> ModuleHealthStatus:
    for dependency in result.dependencies:
        if dependency.name in {"openai_embeddings", "embedding_provider"}:
            dependency.required = False
            dependency.healthy = False
            dependency.detail = detail or dependency.detail
    result.healthy = True
    result.message = ""
    return result
