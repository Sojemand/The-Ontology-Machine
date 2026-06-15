"""Thin stateful surface for the static Vision extractor registry."""
from __future__ import annotations

from pathlib import Path

from ..models import ExtractResult, IngestionConfig, PluginManifest, PluginRegistryEntry
from . import adapter, policy, validation, workflow


class ExtractorRegistry:
    """Static extractor registry for the self-contained Optimizer."""

    def __init__(self, plugins_dir: Path, config: IngestionConfig):
        self._dir = Path(plugins_dir)
        self._bundled_dir = Path(__file__).resolve().parents[2] / "plugins"
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
    def list_extractors(self) -> list[PluginManifest]: return [self._manifests[name] for name in policy._EXTRACTOR_ORDER if name in self._manifests]
    def list_plugins(self) -> list[PluginManifest]: return self.list_extractors()
    def get_manifest(self, name: str) -> PluginManifest | None: return self._manifests.get(name)
    def invoke(self, name: str, file_path: Path, config_override: dict | None = None, *, worker_startup_config: dict | None = None) -> ExtractResult: return workflow.invoke(self, name, file_path, config_override, worker_startup_config=worker_startup_config)
    def _invoke_inline(self, name: str, file_path: Path, config_override: dict | None = None) -> ExtractResult: return workflow.invoke_inline(self, name, file_path, config_override)
    @staticmethod
    def _parse_result(data) -> ExtractResult: return validation.parse_result(data)
    def selftest(self, name: str, timeout_seconds: int | None = None) -> tuple[bool, str]: return workflow.selftest(self, name, timeout_seconds=timeout_seconds)
    def shutdown_workers(self) -> None: return None
    def kill_all(self) -> None: return None
