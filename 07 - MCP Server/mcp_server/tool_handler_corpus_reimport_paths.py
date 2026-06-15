from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .tool_handler_deps import *

SUCCESS_DISPOSITIONS = {"success", "needs_review"}
MAX_PREVIEW_LIMIT = 100


def active_corpus_hashes(db_path: Path) -> tuple[set[str], int]:
    if not db_path.exists() or not db_path.is_file():
        raise ToolFailure(f"Selected Database existiert nicht: {db_path}")
    try:
        conn = sqlite3.connect(f"{db_path.as_uri()}?mode=ro", uri=True)
        try:
            columns = table_columns(conn, "documents")
            if "content_hash" not in columns:
                return set(), 0
            archived = "WHERE COALESCE(is_archived, 0) = 0" if "is_archived" in columns else ""
            rows = conn.execute(f"SELECT content_hash FROM documents {archived}").fetchall()
            hashes = {str(row[0] or "").strip() for row in rows if str(row[0] or "").strip()}
            return hashes, len(rows)
        finally:
            conn.close()
    except sqlite3.DatabaseError as exc:
        raise ToolFailure(f"Selected Database ist nicht als SQLite-DB lesbar: {db_path}") from exc


def pipeline_state_documents() -> tuple[Path, dict[str, Any]]:
    state_path = module_spec("orchestrator").root / "state" / "pipeline" / "pipeline_state.json"
    payload = _read_json_file(state_path)
    documents = payload.get("documents") if isinstance(payload, dict) else {}
    return state_path, documents if isinstance(documents, dict) else {}


def record_belongs_to_active_workspace(record: dict[str, Any], input_root: Path, artifact_root: Path) -> bool:
    for key in ("source_path", "original_source_path"):
        for path in resolve_record_path_candidates(str(record.get(key) or ""), input_root, artifact_root):
            if _is_within(path, input_root) or _is_within(path, artifact_root):
                return True
    for path in _record_artifact_paths(record):
        resolved = path.expanduser().resolve() if path.is_absolute() else (artifact_root / path).resolve()
        if _is_within(resolved, artifact_root):
            return True
    return False


def record_original_source(record: dict[str, Any], artifact_root: Path, originals_root: Path) -> Path | None:
    candidates: list[Path] = []
    for key in ("source_path", "original_source_path"):
        candidates.extend(resolve_original_candidates(str(record.get(key) or ""), artifact_root, originals_root))
    for text in (safe_relative_text(record.get("relative_path")), safe_relative_text(record.get("file_name"))):
        if text:
            candidates.append((originals_root / text).resolve())
    for path in dedupe_paths(candidates):
        if path.is_file() and _is_within(path, originals_root):
            return path
    return None


def resolve_original_candidates(path_text: str, artifact_root: Path, originals_root: Path) -> list[Path]:
    if not path_text.strip():
        return []
    raw = Path(path_text)
    if raw.is_absolute():
        return [raw.expanduser().resolve()]
    safe = safe_relative_text(path_text)
    if not safe:
        return []
    return [(artifact_root / safe).resolve(), (originals_root / safe).resolve()]


def resolve_record_path_candidates(path_text: str, input_root: Path, artifact_root: Path) -> list[Path]:
    if not path_text.strip():
        return []
    raw = Path(path_text)
    if raw.is_absolute():
        return [raw.expanduser().resolve()]
    safe = safe_relative_text(path_text)
    return [(input_root / safe).resolve(), (artifact_root / safe).resolve()] if safe else []


def target_relative_path(record: dict[str, Any], source_path: Path, originals_root: Path) -> Path:
    try:
        return source_path.relative_to(originals_root)
    except ValueError:
        pass
    relative = safe_relative_text(record.get("relative_path"))
    return Path(relative) if relative else Path(source_path.name)


def target_for_input(input_root: Path, relative_path: Path, content_hash: str, *, conflict_policy_value: str) -> tuple[Path, str]:
    target = (input_root / relative_path).resolve()
    if not _is_within(target, input_root):
        raise ToolFailure(f"Reimport-Ziel wuerde ausserhalb des Input-Folders liegen: {target}")
    if not target.exists():
        return target, "copy"
    if hash_file(target) == content_hash:
        return target, "already_in_input"
    if conflict_policy_value == "skip":
        return target, "skip_conflict"
    return renamed_target(target, content_hash, input_root), "rename_conflict"


def renamed_target(target: Path, content_hash: str, input_root: Path) -> Path:
    suffix = content_hash.replace("sha256:", "")[:8] or "reimport"
    for index in range(100):
        extra = f".reimport-{suffix}" if index == 0 else f".reimport-{suffix}-{index}"
        candidate = target.with_name(f"{target.stem}{extra}{target.suffix}").resolve()
        if not _is_within(candidate, input_root):
            raise ToolFailure(f"Reimport-Konfliktziel wuerde ausserhalb des Input-Folders liegen: {candidate}")
        if not candidate.exists() or hash_file(candidate) == content_hash:
            return candidate
    raise ToolFailure(f"Kein konfliktfreier Reimport-Dateiname gefunden fuer: {target}")


def blocked_entry(record: dict[str, Any], status: str, content_hash: str, input_root: Path, source_path: Path | None = None) -> dict[str, Any]:
    relative = safe_relative_text(record.get("relative_path")) or str(record.get("file_name") or "")
    return {
        "status": status,
        "content_hash": content_hash,
        "file_name": str(record.get("file_name") or ""),
        "source_path": str(source_path or record.get("source_path") or ""),
        "target_path": str(input_root / (relative or "missing-source")),
        "target_relative_path": relative,
        "pipeline_relative_path": relative,
        "final_disposition": str(record.get("final_disposition") or ""),
    }


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    try:
        return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
    except sqlite3.DatabaseError:
        return set()


def count_files(root: Path) -> int:
    return sum(1 for path in root.rglob("*") if path.is_file()) if root.exists() and root.is_dir() else 0


def preview_limit(arguments: dict[str, Any]) -> int:
    return min(_positive_int(arguments.get("max_preview", 20), "max_preview"), MAX_PREVIEW_LIMIT)


def conflict_policy(arguments: dict[str, Any]) -> str:
    value = _optional_text(arguments, "conflict_policy") or "rename"
    if value not in {"rename", "skip"}:
        raise ToolFailure("conflict_policy muss 'rename' oder 'skip' sein.")
    return value


def optional_positive_int(arguments: dict[str, Any], key: str) -> int | None:
    return None if key not in arguments or arguments.get(key) in (None, "") else _positive_int(arguments.get(key), key)


def safe_relative_text(value: Any) -> str:
    text = str(value or "").strip().replace("\\", "/")
    path = Path(text)
    if not text or path.is_absolute() or path.drive or any(part in {"", ".", ".."} for part in path.parts):
        return ""
    return Path(*path.parts).as_posix()


def relative_to(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def dedupe_paths(paths: list[Path]) -> list[Path]:
    return list(dict.fromkeys(paths))


__all__ = [name for name in globals() if not name.startswith("__")]
