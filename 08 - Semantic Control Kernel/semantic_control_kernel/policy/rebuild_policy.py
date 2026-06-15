from __future__ import annotations

from pathlib import Path
from typing import Mapping

from semantic_control_kernel.repository.paths import canonical_path_text, path_hash


DEFAULT_EMBEDDING_POLICY = "optional_if_unconfigured"


def resolve_rebuild_target_path(artifact_root: str | Path, target_database_name: str) -> Path:
    root = Path(artifact_root).resolve(strict=False)
    name = _database_name(target_database_name)
    target = (root / "Corpus" / name).resolve(strict=False)
    corpus = (root / "Corpus").resolve(strict=False)
    try:
        target.relative_to(corpus)
    except ValueError as exc:
        raise ValueError("Rebuild target database path must stay inside the selected Artifact Tree Corpus folder.") from exc
    return target


def target_identity(artifact_root: str | Path, target_database_path: str | Path) -> dict[str, str]:
    return {
        "artifact_root": str(Path(artifact_root).resolve(strict=False)),
        "artifact_root_path_hash": path_hash(artifact_root),
        "target_database_path": str(Path(target_database_path).resolve(strict=False)),
        "target_database_path_hash": path_hash(target_database_path),
    }


def overwrite_receipt_matches(
    receipt: Mapping[str, object] | None,
    *,
    artifact_root: str | Path,
    target_database_path: str | Path,
    loaded_release_fingerprint: str,
    workflow_run_id: str,
) -> bool:
    if not isinstance(receipt, Mapping):
        return False
    if str(receipt.get("status") or receipt.get("user_decision")) not in {"confirmed", "approve", "approved"}:
        return False
    confirmed_target_identity = receipt.get("confirmed_target_identity")
    if isinstance(confirmed_target_identity, Mapping):
        return _confirmed_target_matches(
            confirmed_target_identity,
            artifact_root=artifact_root,
            target_database_path=target_database_path,
            loaded_release_fingerprint=loaded_release_fingerprint,
            workflow_run_id=workflow_run_id,
        )
    return (
        _same_path(receipt.get("artifact_root"), artifact_root)
        and _same_path(receipt.get("target_database_path"), target_database_path)
        and str(receipt.get("loaded_release_fingerprint", "")) == loaded_release_fingerprint
        and str(receipt.get("workflow_run_id", "")) == workflow_run_id
    )


def embedding_result_from_policy(
    *,
    policy: str,
    provider_configured: bool,
    adapter_status: str | None = None,
) -> tuple[str, str | None]:
    if not provider_configured and policy == DEFAULT_EMBEDDING_POLICY:
        return "skipped_unconfigured", None
    if not provider_configured:
        return "blocked", "embedding_provider_unavailable"
    if adapter_status and adapter_status != "ok":
        return "blocked", "embedding_provider_failure"
    return "created", None


def _database_name(value: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError("target_database_name is required.")
    path = Path(text)
    if path.is_absolute() or len(path.parts) != 1 or text in {".", ".."}:
        raise ValueError("target_database_name must be a file name, not a path.")
    return text if path.suffix else f"{text}.db"


def _same_path(left: object, right: str | Path) -> bool:
    if left is None:
        return False
    return canonical_path_text(str(left)) == canonical_path_text(right)


def _confirmed_target_matches(
    target_identity_payload: Mapping[str, object],
    *,
    artifact_root: str | Path,
    target_database_path: str | Path,
    loaded_release_fingerprint: str,
    workflow_run_id: str,
) -> bool:
    database_hash = str(
        target_identity_payload.get("database_path_hash")
        or target_identity_payload.get("target_database_path_hash")
        or ""
    )
    release_fingerprint = str(
        target_identity_payload.get("release_fingerprint")
        or target_identity_payload.get("loaded_release_fingerprint")
        or ""
    )
    return (
        str(target_identity_payload.get("artifact_root_path_hash") or "") == path_hash(artifact_root)
        and database_hash == path_hash(target_database_path)
        and release_fingerprint == loaded_release_fingerprint
        and str(target_identity_payload.get("workflow_run_id") or "") == workflow_run_id
    )
