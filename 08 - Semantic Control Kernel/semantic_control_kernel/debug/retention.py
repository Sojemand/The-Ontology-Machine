from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from semantic_control_kernel.repository.atomic_json import AtomicJsonStore
from semantic_control_kernel.repository.hard_cap import KernelStateHardCapService
from semantic_control_kernel.repository.ids import utc_compact_timestamp
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.validation.debug_validation import validate_support_bundle_cleanup_history


@dataclass(frozen=True)
class SupportBundlePrunePlan:
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.payload)


class SupportBundleRetentionPolicy:
    def __init__(self, paths: StatePaths, support_bundle_store) -> None:
        self.paths = paths
        self.support_bundle_store = support_bundle_store
        self._json = AtomicJsonStore(paths, "support_bundle_retention")

    @staticmethod
    def expires_at_for(*, created_at: str, retention_class: str) -> str | None:
        created = _parse_utc(created_at)
        if retention_class in {"final_error_manual", "support_only_manual", "llm_validation_manual"}:
            return None
        if retention_class == "stale_recovery_90_days":
            return _iso(created + timedelta(days=90))
        if retention_class == "operator_snapshot_30_days":
            return _iso(created + timedelta(days=30))
        if retention_class == "test_fixture_disposable":
            return _iso(created + timedelta(hours=1))
        raise ValueError(f"Unknown retention_class: {retention_class}")

    def plan_prune(self, now_utc: str, dry_run: bool = True) -> SupportBundlePrunePlan:
        expired_bundle_ids: list[str] = []
        retained_bundle_ids: list[str] = []
        for manifest in self.support_bundle_store.list_bundle_manifests():
            support_bundle_id = str(manifest["support_bundle_id"])
            expires_at = manifest.get("expires_at")
            if isinstance(expires_at, str) and _parse_utc(expires_at) <= _parse_utc(now_utc):
                expired_bundle_ids.append(support_bundle_id)
            else:
                retained_bundle_ids.append(support_bundle_id)
        payload = {
            "schema_version": "debug.support_bundle_prune_plan.v1",
            "planned_at": now_utc,
            "dry_run": dry_run,
            "expired_bundle_ids": expired_bundle_ids,
            "retained_bundle_ids": retained_bundle_ids,
        }
        return SupportBundlePrunePlan(payload)

    def apply_prune(self, plan: SupportBundlePrunePlan | Mapping[str, Any], operator_reason: str) -> dict[str, Any]:
        payload = dict(plan.to_dict() if isinstance(plan, SupportBundlePrunePlan) else plan)
        if payload.get("schema_version") != "debug.support_bundle_prune_plan.v1":
            raise ValueError("Support bundle prune plan has an invalid schema_version.")
        if payload.get("dry_run") is not True:
            raise ValueError("Support bundle prune plan must provide dry-run evidence before deletion.")
        planned_at = str(payload.get("planned_at") or utc_iso())
        expired_bundle_ids = [str(item) for item in payload.get("expired_bundle_ids", [])]
        retained_bundle_ids = [str(item) for item in payload.get("retained_bundle_ids", [])]
        deleted_bundle_ids: list[str] = []
        for support_bundle_id in expired_bundle_ids:
            if not self._is_bundle_expired_at(support_bundle_id, planned_at):
                if support_bundle_id not in retained_bundle_ids:
                    retained_bundle_ids.append(support_bundle_id)
                continue
            if self.support_bundle_store.delete_bundle(support_bundle_id):
                deleted_bundle_ids.append(support_bundle_id)
        cleanup_id = f"cleanup_{utc_compact_timestamp()}"
        history = {
            "schema_version": "debug.support_bundle_cleanup_history.v1",
            "cleanup_id": cleanup_id,
            "created_at": utc_iso(),
            "operator_reason": operator_reason,
            "deleted_bundle_ids": deleted_bundle_ids,
            "retained_bundle_ids": retained_bundle_ids,
            "expired_bundle_ids": expired_bundle_ids,
            "dry_run": False,
        }
        validate_support_bundle_cleanup_history(history)
        history_path = self.paths.state_root / "support" / "cleanup_history" / f"{cleanup_id}.json"
        self._json.write_json(history_path, history, immutable=True, validator=validate_support_bundle_cleanup_history)
        KernelStateHardCapService(self.paths).prune_support_cleanup_history()
        return history

    def _is_bundle_expired_at(self, support_bundle_id: str, now_utc: str) -> bool:
        try:
            manifest = self.support_bundle_store.get_manifest(support_bundle_id)
        except Exception:
            return False
        expires_at = manifest.get("expires_at")
        return isinstance(expires_at, str) and _parse_utc(expires_at) <= _parse_utc(now_utc)


def _parse_utc(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
