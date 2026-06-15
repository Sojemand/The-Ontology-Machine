"""Workflow for live discovery with cache fallback."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from ..repository import load_registry_cache, save_registry_cache
from .contract_probe import probe_contract
from . import policy, types


def _runtime_available(module_root: Path) -> bool:
    for candidate in ("python.exe", "Scripts/python.exe", "bin/python"):
        if (module_root / "runtime" / "python" / Path(candidate)).is_file():
            return True
    return False


def _load_manifest(module_root: Path) -> tuple[dict | None, str]:
    manifest_path = module_root / "module-manifest.json"
    if not manifest_path.exists():
        return None, ""
    try:
        import json

        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, str(exc)
    if not isinstance(payload, dict):
        return None, "module-manifest.json must be a JSON object."
    return payload, ""


def _contract_readiness(module_root: Path, manifest: dict) -> tuple[str, str]:
    candidate = policy.manifest_contract_candidate(module_root, manifest)
    if candidate is None:
        candidates = policy.contract_candidates(module_root)
        if not candidates:
            return "missing_edit_contract", ""
        candidate = candidates[0]
    required = [candidate / f"{name}.py" for name in policy.REQUIRED_CONTRACT_ACTIONS]
    main_path = candidate / "__main__.py"
    init_path = candidate / "__init__.py"
    if candidate.is_dir() and init_path.exists() and main_path.exists() and all(path.exists() for path in required):
        return "ready", str(candidate)
    return "contract_error", str(candidate)


def _blockers(readiness: str, *, runtime_available: bool) -> tuple[str, ...]:
    blockers: list[str] = []
    if readiness != "ready":
        blockers.append(readiness)
    if not runtime_available:
        blockers.append("runtime_unavailable")
    return tuple(blockers)


def _discover_entry(module_root: Path) -> types.ModuleReadinessEntry:
    manifest_path = module_root / "module-manifest.json"
    runtime_available = _runtime_available(module_root)
    if policy.is_placeholder_dir(module_root):
        readiness, contract_path, module_key = "placeholder_module", "", ""
        manifest_present, display_name = False, module_root.name
    else:
        manifest, manifest_error = _load_manifest(module_root)
        manifest_present = manifest_path.exists()
        if manifest is None:
            readiness = "manifest_error" if manifest_present else "missing_manifest"
            contract_path, module_key = "", ""
            display_name = module_root.name
        else:
            readiness, contract_path = _contract_readiness(module_root, manifest)
            module_key = str(manifest.get("module_key") or "")
            display_name = str(manifest.get("display_name") or module_root.name)
    return types.ModuleReadinessEntry(
        slot_name=module_root.name,
        display_name=display_name,
        module_root=str(module_root.resolve()),
        module_key=module_key,
        readiness=readiness,
        blockers=_blockers(readiness, runtime_available=runtime_available),
        manifest_path=str(manifest_path.resolve()),
        manifest_present=manifest_present,
        edit_contract_path=contract_path,
        runtime_available=runtime_available,
        diagnostic=manifest_error if readiness == "manifest_error" else "",
    )


def _probe_ready_entries(entries: tuple[types.ModuleReadinessEntry, ...], *, state_root: Path) -> tuple[types.ModuleReadinessEntry, ...]:
    indexed = [(index, entry) for index, entry in enumerate(entries) if entry.readiness == "ready" and entry.runtime_available]
    if not indexed:
        return entries

    def probe_entry(entry: types.ModuleReadinessEntry) -> types.ModuleReadinessEntry:
        diagnostic = probe_contract(Path(entry.module_root), entry.edit_contract_path, state_root=state_root)
        if not diagnostic:
            return entry
        return replace(
            entry,
            readiness="contract_error",
            blockers=_blockers("contract_error", runtime_available=entry.runtime_available),
            diagnostic=diagnostic,
        )

    updates: list[tuple[int, types.ModuleReadinessEntry]] = []
    max_workers = min(policy.REGISTRY_PROBE_MAX_WORKERS, len(indexed))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [(index, executor.submit(probe_entry, entry)) for index, entry in indexed]
        for index, future in futures:
            updates.append((index, future.result()))

    updated = list(entries)
    for index, entry in updates:
        updated[index] = entry
    return tuple(updated)


def _live_snapshot(pipeline_root: Path, *, state_root: Path | None = None, probe_contracts: bool = True) -> types.RegistrySnapshot:
    entries = tuple(_discover_entry(path) for path in policy.candidate_dirs(pipeline_root))
    if state_root is not None and probe_contracts:
        entries = _probe_ready_entries(entries, state_root=state_root)
    return types.RegistrySnapshot(
        generated_at=datetime.now(timezone.utc).isoformat(),
        source="live",
        stale=False,
        message="",
        entries=entries,
    )


def discover_registry(pipeline_root: Path, *, state_root: Path | None = None, probe_contracts: bool = True) -> types.RegistrySnapshot:
    try:
        snapshot = _live_snapshot(pipeline_root, state_root=state_root, probe_contracts=probe_contracts)
    except Exception as exc:
        if state_root is None:
            raise
        cached = load_registry_cache(state_root)
        if cached is None:
            raise
        stale = types.RegistrySnapshot.from_dict(cached)
        return types.RegistrySnapshot(
            generated_at=stale.generated_at,
            source="cache",
            stale=True,
            message=str(exc),
            entries=stale.entries,
        )
    if state_root is not None:
        save_registry_cache(state_root, snapshot.to_dict())
    return snapshot
