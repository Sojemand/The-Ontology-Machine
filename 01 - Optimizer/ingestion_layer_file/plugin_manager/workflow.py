"""Workflow orchestration for manifest load, invocation and selftests."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess

from ..models import ExtractResult, PluginRegistryEntry
from . import debug, policy


def load_manifests(registry) -> None:
    for name in (policy._INLINE_NAME_TEXT, policy._INLINE_NAME_PDF):
        registry._manifests[name] = policy._INLINE_EXTRACTORS[name].manifest
        registry.plugins[name] = PluginRegistryEntry(enabled=True, installed_at="", healthy=True)

    for name in (
        policy._PLUGIN_NAME_DOCX,
        policy._PLUGIN_NAME_ODT,
        policy._PLUGIN_NAME_RTF,
        policy._PLUGIN_NAME_MAIL_RFC822,
        policy._PLUGIN_NAME_MAIL_OUTLOOK_MSG,
        policy._PLUGIN_NAME_MAIL_OUTLOOK_STORE,
    ):
        manifest = registry._load_manifest(registry._plugin_dir(name), name) or policy.default_plugin_manifest(name)
        manifest.formats = list(policy._EXPLICIT_FORMATS[name])
        manifest.also_handles = []
        registry._manifests[name] = manifest
        registry.plugins[name] = PluginRegistryEntry(enabled=True, installed_at="", healthy=True)

    registry.format_routing = policy.build_format_routing(registry._manifests)


def invoke(registry, name: str, file_path: Path, config_override: dict | None = None) -> ExtractResult:
    if policy.is_inline_extractor(name):
        return registry._invoke_inline(name, file_path, config_override)
    if policy.is_subprocess_extractor(name):
        return registry._invoke_subprocess(name, file_path, config_override)
    return ExtractResult(status="error", errors=[f"Extractor {name} nicht gefunden"])


def invoke_inline(registry, name: str, file_path: Path, config_override: dict | None = None) -> ExtractResult:
    runtime = policy._INLINE_EXTRACTORS[name]
    try:
        payload = runtime.extract(file_path, config_override or runtime.manifest.config)
    except Exception as exc:
        debug.log_inline_extract_failed(name, file_path, exc)
        return ExtractResult(status="error", errors=[f"Inline-Extractor {name} fehlgeschlagen: {exc}"])
    return registry._parse_result(payload)


def invoke_subprocess(registry, name: str, file_path: Path, config_override: dict | None = None) -> ExtractResult:
    manifest = registry._manifests.get(name)
    extractor = registry._plugin_dir(name) / "extractor.py"
    if not extractor.exists():
        return ExtractResult(status="error", errors=[f"extractor.py fehlt fuer {name}"])

    cfg = dict(config_override or (manifest.config if manifest else {}))
    try:
        python = registry._resolve_plugin_python(name)
        env = registry._plugin_subprocess_env(name)
    except Exception as exc:
        return ExtractResult(status="error", errors=[str(exc)])

    cmd = [str(python), str(extractor), "--extract", "--input", str(file_path), "--config", json.dumps(cfg, ensure_ascii=False)]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=registry._config.plugin_timeout_seconds,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return ExtractResult(status="error", errors=[f"Timeout ({registry._config.plugin_timeout_seconds}s)"])
    except Exception as exc:
        return ExtractResult(status="error", errors=[str(exc)])

    if result.returncode != 0:
        return ExtractResult(status="error", errors=[result.stderr[:500] or f"Exit code {result.returncode}"])
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return ExtractResult(status="error", errors=[f"Ungueltiges JSON: {exc}"])
    return registry._parse_result(payload)


def selftest(registry, name: str, *, timeout_seconds: int = 30) -> tuple[bool, str]:
    if policy.is_inline_extractor(name):
        payload = policy._INLINE_EXTRACTORS[name].selftest()
        if payload.get("status") == "ok":
            return True, f"OK (v{payload.get('version', '?')})"
        return False, payload.get("message") or payload.get("error") or "Unbekannter Fehler"

    extractor = registry._plugin_dir(name) / "extractor.py"
    if not extractor.exists():
        return False, f"extractor.py nicht gefunden in {registry._plugin_dir(name)}"
    try:
        python = registry._resolve_plugin_python(name)
        env = registry._plugin_subprocess_env(name)
        result = subprocess.run(
            [str(python), str(extractor), "--selftest"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return False, f"Selftest Timeout ({timeout_seconds}s)"
    except Exception as exc:
        return False, str(exc)

    if result.returncode != 0:
        return False, result.stderr[:500] or f"Exit code {result.returncode}"
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False, "Ungueltiges JSON"
    if payload.get("status") == "ok":
        return True, f"OK (v{payload.get('version', '?')})"
    return False, payload.get("message") or payload.get("error") or "Unbekannter Fehler"


def shutdown_workers(_registry) -> None:
    return None


def kill_all(_registry) -> None:
    return None
