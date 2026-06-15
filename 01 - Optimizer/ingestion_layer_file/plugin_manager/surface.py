"""Thin stateful surface for the plugin manager package."""
from __future__ import annotations

from pathlib import Path

from ..models import ExtractResult, IngestionConfig, PluginManifest, PluginRegistryEntry
from ..paths import resolve_layout
from . import adapter, policy, validation, workflow


class ExtractorRegistry:
    """Static extractor registry for the self-contained Optimizer."""

    def __init__(self, plugins_dir: Path, config: IngestionConfig):
        self._dir = Path(plugins_dir)
        self._layout = resolve_layout(self._dir.parent)
        self._root = self._layout.module_root
        self._config = config
        self.plugins: dict[str, PluginRegistryEntry] = {}
        self.format_routing: dict[str, str] = {}
        self._manifests: dict[str, PluginManifest] = {}
        self._load_manifests()

    def _load_manifests(self) -> None: workflow.load_manifests(self)
    def _plugin_dir(self, name: str) -> Path: return adapter.plugin_dir(self, name)
    @staticmethod
    def _load_manifest(plugin_dir: Path, fallback_name: str) -> PluginManifest | None: return adapter.load_manifest(plugin_dir, fallback_name)
    def get_plugin_for_format(self, ext: str) -> str | None: return self.format_routing.get(str(ext).lower())
    def list_extractors(self) -> list[PluginManifest]: return policy.ordered_manifests(self._manifests)
    def list_plugins(self) -> list[PluginManifest]: return self.list_extractors()
    def get_manifest(self, name: str) -> PluginManifest | None: return self._manifests.get(name)
    def invoke(self, name: str, file_path: Path, config_override: dict | None = None) -> ExtractResult: return workflow.invoke(self, name, file_path, config_override)
    def _invoke_inline(self, name: str, file_path: Path, config_override: dict | None = None) -> ExtractResult: return workflow.invoke_inline(self, name, file_path, config_override)
    def _invoke_subprocess(self, name: str, file_path: Path, config_override: dict | None = None) -> ExtractResult: return workflow.invoke_subprocess(self, name, file_path, config_override)
    @staticmethod
    def _parse_result(data) -> ExtractResult: return validation.parse_result(data)
    def selftest(self, name: str, timeout_seconds: int = 30) -> tuple[bool, str]: return workflow.selftest(self, name, timeout_seconds=timeout_seconds)
    def shutdown_workers(self) -> None: workflow.shutdown_workers(self)
    def kill_all(self) -> None: workflow.kill_all(self)
    def _resolve_python(self) -> Path: return adapter.resolve_python(self)
    def _bundled_python_candidates(self) -> tuple[Path, ...]: return adapter.bundled_python_candidates(self)
    def _subprocess_env(self) -> dict[str, str]: return adapter.subprocess_env(self)
    def _plugin_runtime_root(self, name: str) -> Path: return adapter.plugin_runtime_root(self, name)
    def _plugin_bundled_python_candidates(self, name: str) -> tuple[Path, ...]: return adapter.plugin_bundled_python_candidates(self, name)
    @staticmethod
    def _validate_runtime_root(runtime_root: Path, name: str) -> None: validation.validate_runtime_root(runtime_root, name)
    def _ensure_venv(self, name: str) -> Path: return adapter.ensure_plugin_runtime(self, name)
    def _resolve_plugin_python(self, name: str) -> Path: return adapter.resolve_plugin_python(self, name)
    def _plugin_subprocess_env(self, name: str) -> dict[str, str]: return adapter.plugin_subprocess_env(self, name)

