from __future__ import annotations

from .tool_handler_deps import *

_NORMALIZE_KEYS = frozenset(
    {
        "structured_path",
        "structured_root",
        "normalized_output_path",
        "normalized_root",
        "corpus_db_path",
        "corpus_output_folder",
        "runtime_settings",
        "timeout_seconds",
    }
)
_HEALTHCHECK_KEYS = frozenset({"runtime_settings", "corpus_db_path", "corpus_output_folder", "timeout_seconds"})
_RUNTIME_SETTINGS_KEYS = frozenset({"model", "max_output_tokens"})


def normalizer_normalize_document(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, _NORMALIZE_KEYS, "normalizer.normalize_document")
    structured_root = _existing_dir(arguments, "structured_root")
    normalized_root = _existing_dir(arguments, "normalized_root")
    structured_path = _structured_json_path(arguments, "structured_path", root=structured_root)
    normalized_output_path = _normalized_json_output_path(arguments, "normalized_output_path", root=normalized_root)
    runtime_settings = _runtime_settings(arguments)
    timeout = _timeout_seconds(arguments)
    release_context, release = _active_release_context(arguments, required=True, timeout=timeout)
    payload = {
        "action": "normalize_document",
        "structured_path": str(structured_path),
        "normalized_output_path": str(normalized_output_path),
        "runtime_settings": runtime_settings,
        "release": release,
    }
    result = _invoke_normalizer(payload, timeout=timeout)
    return {**result, "release_context": release_context}


def normalizer_healthcheck(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, _HEALTHCHECK_KEYS, "normalizer.healthcheck")
    runtime_settings = _runtime_settings(arguments)
    timeout = _timeout_seconds(arguments)
    release_context, _release = _active_release_context(arguments, required=False, timeout=timeout)
    result = _invoke_normalizer({"action": "healthcheck", "runtime_settings": runtime_settings}, timeout=timeout)
    return {**result, "release_context": release_context}


def _invoke_normalizer(payload: dict[str, Any], *, timeout: int | None) -> dict[str, Any]:
    if timeout is None:
        return _invoke_product("normalizer", payload)
    return _invoke_product("normalizer", payload, timeout=timeout)


def _active_release_context(
    arguments: dict[str, Any],
    *,
    required: bool,
    timeout: int | None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    corpus_db_path = _corpus_db(arguments, required=required)
    if corpus_db_path is None:
        return {"checked": False, "source": "not_requested"}, None
    payload = {"action": "read_active_semantic_release", "corpus_db_path": str(corpus_db_path)}
    response = _invoke_product("corpus_builder", payload, timeout=timeout) if timeout is not None else _invoke_product("corpus_builder", payload)
    detail, release = _extract_active_release(response)
    status = detail.get("status") if isinstance(detail.get("status"), dict) else {}
    snapshot = detail.get("active_snapshot") if isinstance(detail.get("active_snapshot"), dict) else {}
    return (
        {
            "checked": True,
            "source": "corpus_builder.read_active_semantic_release",
            "corpus_db_path": str(corpus_db_path),
            "release_id": str(detail.get("release_id") or release.get("release_id") or ""),
            "release_version": str(detail.get("release_version") or release.get("release_version") or ""),
            "fingerprint": str(detail.get("fingerprint") or release.get("fingerprint") or ""),
            "active_snapshot_id": str(snapshot.get("snapshot_id") or ""),
            "runtime_truth_source": str(status.get("runtime_truth_source") or ""),
        },
        release,
    )


def _extract_active_release(response: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    status = str(response.get("status") or "").casefold()
    if status in {"error", "failed"}:
        reason = str(response.get("reason") or response.get("message") or "Corpus Builder lieferte keinen aktiven Semantic Release.")
        raise ToolFailure(reason)
    detail = response.get("detail") if isinstance(response.get("detail"), dict) else response
    release = detail.get("release") if isinstance(detail, dict) else None
    if not isinstance(release, dict) or not release:
        raise ToolFailure("read_active_semantic_release lieferte keinen release-Payload.")
    return detail, release


def _corpus_db(arguments: dict[str, Any], *, required: bool) -> Path | None:
    raw = _required_text(arguments, "corpus_db_path") if required else _optional_text(arguments, "corpus_db_path")
    if not raw:
        return None
    _validate_existing_context_target(raw, _corpus_output_folder(arguments, raw))
    return Path(raw).expanduser().resolve()


def _runtime_settings(arguments: dict[str, Any]) -> dict[str, Any]:
    settings = _required_mapping(arguments, "runtime_settings")
    unknown = sorted(set(settings) - _RUNTIME_SETTINGS_KEYS)
    if unknown:
        raise ToolFailure(f"runtime_settings kennt diese Felder nicht: {', '.join(unknown)}")
    model = _required_nested_text(settings, "runtime_settings.model")
    max_output_tokens = _positive_int(settings.get("max_output_tokens"), "runtime_settings.max_output_tokens")
    return {"model": model, "max_output_tokens": max_output_tokens}


def _required_nested_text(payload: dict[str, Any], label: str) -> str:
    key = label.rsplit(".", 1)[-1]
    value = payload.get(key)
    if value is None:
        raise ToolFailure(f"{label} fehlt oder ist ungueltig.")
    if not isinstance(value, str):
        raise ToolFailure(f"{label} muss ein String sein.")
    text = value.strip()
    if not text:
        raise ToolFailure(f"{label} fehlt oder ist ungueltig.")
    return text


def _existing_dir(arguments: dict[str, Any], key: str) -> Path:
    path = Path(_required_text(arguments, key)).expanduser().resolve()
    if not path.exists():
        raise ToolFailure(f"{key} existiert nicht: {path}")
    if not path.is_dir():
        raise ToolFailure(f"{key} muss ein Ordner sein: {path}")
    return path


def _structured_json_path(arguments: dict[str, Any], key: str, *, root: Path) -> Path:
    path = _resolve_under_root(_required_text(arguments, key), root=root, key=key)
    if not path.name.casefold().endswith(".structured.json"):
        raise ToolFailure(f"{key} muss auf .structured.json enden.")
    if not path.exists():
        raise ToolFailure(f"{key} existiert nicht: {path}")
    if not path.is_file():
        raise ToolFailure(f"{key} muss eine Datei sein: {path}")
    return path


def _normalized_json_output_path(arguments: dict[str, Any], key: str, *, root: Path) -> Path:
    path = _resolve_under_root(_required_text(arguments, key), root=root, key=key)
    if path.suffix.casefold() != ".json":
        raise ToolFailure(f"{key} muss eine JSON-Datei sein.")
    if path.exists() and path.is_dir():
        raise ToolFailure(f"{key} muss eine Datei sein: {path}")
    return path


def _resolve_under_root(value: str, *, root: Path, key: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = root / path
    resolved = path.resolve()
    if not _is_within(resolved, root):
        raise ToolFailure(f"{key} muss innerhalb der angegebenen Root liegen.")
    return resolved


def _timeout_seconds(arguments: dict[str, Any]) -> int | None:
    if "timeout_seconds" not in arguments or arguments.get("timeout_seconds") in (None, ""):
        return None
    return _positive_int(arguments["timeout_seconds"], "timeout_seconds")


def _reject_unknown(arguments: dict[str, Any], allowed: frozenset[str], tool_name: str) -> None:
    unknown = sorted(set(arguments) - set(allowed))
    if unknown:
        raise ToolFailure(f"{tool_name} kennt diese Argumente nicht: {', '.join(unknown)}")


__all__ = [name for name in globals() if not name.startswith("__")]
