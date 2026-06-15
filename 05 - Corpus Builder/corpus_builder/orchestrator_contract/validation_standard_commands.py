from __future__ import annotations

from .types import (
    BackfillStaleCommand,
    BasicRelationMiningCommand,
    CreateAndRebuildNewCorpusDbCommand,
    ExportCommand,
    LoadSemanticReleaseCommand,
    MergeCorpusDatabasesCommand,
    MergePreflightCommand,
    PreviewRebuildFromArtifactsCommand,
    ReadActiveSemanticReleaseCommand,
    RebuildFromArtifactsCommand,
    ResetActiveCorpusDbCommand,
    SearchCommand,
    SemanticAuditCommand,
    SemanticStatusCommand,
    StatsCommand,
)
from .validation_common import parse_bool, parse_optional_int, parse_string_list, reject_unknown_keys, required_string
from .validation_keys import (
    _BACKFILL_STALE_KEYS,
    _BASIC_RELATION_MINING_KEYS,
    _CREATE_AND_REBUILD_NEW_CORPUS_DB_KEYS,
    _EXPORT_KEYS,
    _LOAD_SEMANTIC_RELEASE_KEYS,
    _MERGE_CORPUS_DATABASES_KEYS,
    _MERGE_PREFLIGHT_KEYS,
    _PREVIEW_REBUILD_KEYS,
    _READ_ACTIVE_SEMANTIC_RELEASE_KEYS,
    _REBUILD_KEYS,
    _RESET_ACTIVE_CORPUS_DB_KEYS,
    _SEARCH_KEYS,
    _SEMANTIC_AUDIT_KEYS,
    _SEMANTIC_STATUS_KEYS,
    _STATS_KEYS,
)


def parse_semantic_status_command(payload: dict) -> SemanticStatusCommand:
    reject_unknown_keys(payload, _SEMANTIC_STATUS_KEYS)
    return SemanticStatusCommand(corpus_db_path=_optional_text(payload, "corpus_db_path"))


def parse_read_active_semantic_release_command(payload: dict) -> ReadActiveSemanticReleaseCommand:
    reject_unknown_keys(payload, _READ_ACTIVE_SEMANTIC_RELEASE_KEYS)
    return ReadActiveSemanticReleaseCommand(corpus_db_path=_optional_text(payload, "corpus_db_path"))


def parse_load_semantic_release_command(payload: dict) -> LoadSemanticReleaseCommand:
    reject_unknown_keys(payload, _LOAD_SEMANTIC_RELEASE_KEYS)
    return LoadSemanticReleaseCommand(
        release_path=required_string(payload, "release_path") or _missing("release_path"),
        corpus_db_path=_optional_text(payload, "corpus_db_path"),
        write_global_mirrors=parse_bool(payload, "write_global_mirrors", default=True),
    )


def parse_reset_active_corpus_db_command(payload: dict) -> ResetActiveCorpusDbCommand:
    reject_unknown_keys(payload, _RESET_ACTIVE_CORPUS_DB_KEYS)
    return ResetActiveCorpusDbCommand(
        confirmation_artifact_path=required_string(payload, "confirmation_artifact_path") or _missing("confirmation_artifact_path"),
        corpus_db_path=_optional_text(payload, "corpus_db_path"),
    )


def parse_semantic_audit_command(payload: dict) -> SemanticAuditCommand:
    reject_unknown_keys(payload, _SEMANTIC_AUDIT_KEYS)
    return SemanticAuditCommand(corpus_db_path=_optional_text(payload, "corpus_db_path"))


def parse_backfill_stale_command(payload: dict) -> BackfillStaleCommand:
    reject_unknown_keys(payload, _BACKFILL_STALE_KEYS)
    return BackfillStaleCommand(
        corpus_db_path=_optional_text(payload, "corpus_db_path"),
        document_ids=parse_string_list(payload, "document_ids"),
        stale_only=parse_bool(payload, "stale_only", default=True),
        limit=parse_optional_int(payload, "limit"),
    )


def parse_merge_preflight_command(payload: dict) -> MergePreflightCommand:
    reject_unknown_keys(payload, _MERGE_PREFLIGHT_KEYS)
    return MergePreflightCommand(
        source_db_path=required_string(payload, "source_db_path") or _missing("source_db_path"),
        target_db_path=required_string(payload, "target_db_path") or _missing("target_db_path"),
    )


def parse_merge_corpus_databases_command(payload: dict) -> MergeCorpusDatabasesCommand:
    reject_unknown_keys(payload, _MERGE_CORPUS_DATABASES_KEYS)
    return MergeCorpusDatabasesCommand(
        source_db_path=required_string(payload, "source_db_path") or _missing("source_db_path"),
        target_db_path=required_string(payload, "target_db_path") or _missing("target_db_path"),
        snapshot_risk_confirmation_artifact_path=_optional_text(payload, "snapshot_risk_confirmation_artifact_path"),
        collision_resolution_artifact_path=_optional_text(payload, "collision_resolution_artifact_path"),
    )


def parse_search_command(payload: dict) -> SearchCommand:
    reject_unknown_keys(payload, _SEARCH_KEYS)
    mode = required_string(payload, "mode") or _missing("mode")
    if mode not in {"Fulltext", "Semantisch", "Hybrid"}:
        raise ValueError("mode muss Fulltext, Semantisch oder Hybrid sein.")
    return SearchCommand(
        corpus_db_path=_optional_text(payload, "corpus_db_path"),
        query=required_string(payload, "query") or _missing("query"),
        mode=mode,
        limit=parse_optional_int(payload, "limit"),
        runtime_model=_optional_text(payload, "runtime_model"),
    )


def parse_stats_command(payload: dict) -> StatsCommand:
    reject_unknown_keys(payload, _STATS_KEYS)
    return StatsCommand(corpus_db_path=_optional_text(payload, "corpus_db_path"))


def parse_export_command(payload: dict) -> ExportCommand:
    reject_unknown_keys(payload, _EXPORT_KEYS)
    fmt = required_string(payload, "fmt") or _missing("fmt")
    if fmt not in {"jsonl", "csv"}:
        raise ValueError("fmt muss jsonl oder csv sein.")
    return ExportCommand(
        corpus_db_path=_optional_text(payload, "corpus_db_path"),
        output_path=required_string(payload, "output_path") or _missing("output_path"),
        fmt=fmt,
        include_archived=parse_bool(payload, "include_archived", default=False),
    )


def parse_preview_rebuild_from_artifacts_command(payload: dict) -> PreviewRebuildFromArtifactsCommand:
    reject_unknown_keys(payload, _PREVIEW_REBUILD_KEYS)
    return PreviewRebuildFromArtifactsCommand(**_artifact_args(payload))


def parse_rebuild_from_artifacts_command(payload: dict) -> RebuildFromArtifactsCommand:
    reject_unknown_keys(payload, _REBUILD_KEYS)
    return RebuildFromArtifactsCommand(replace_existing=parse_bool(payload, "replace_existing", default=True), **_artifact_args(payload))


def parse_create_and_rebuild_new_corpus_db_command(payload: dict) -> CreateAndRebuildNewCorpusDbCommand:
    reject_unknown_keys(payload, _CREATE_AND_REBUILD_NEW_CORPUS_DB_KEYS)
    return CreateAndRebuildNewCorpusDbCommand(
        confirmation_artifact_path=required_string(payload, "confirmation_artifact_path") or _missing("confirmation_artifact_path"),
        **_artifact_args(payload),
    )


def parse_basic_relation_mining_command(payload: dict) -> BasicRelationMiningCommand:
    reject_unknown_keys(payload, _BASIC_RELATION_MINING_KEYS)
    return BasicRelationMiningCommand(
        corpus_db_path=_optional_text(payload, "corpus_db_path"),
        dry_run=parse_bool(payload, "dry_run", default=False),
    )


def _artifact_args(payload: dict) -> dict:
    return {
        "pipeline_root": _optional_text(payload, "pipeline_root"),
        "normalized_dir": _optional_text(payload, "normalized_dir"),
        "structured_dir": _optional_text(payload, "structured_dir"),
        "validation_dir": _optional_text(payload, "validation_dir"),
        "raw_dir": _optional_text(payload, "raw_dir"),
        "corpus_db_path": _optional_text(payload, "corpus_db_path"),
        "release_path": _optional_text(payload, "release_path"),
    }


def _optional_text(payload: dict, key: str) -> str | None:
    value = payload.get(key)
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} muss ein String sein.")
    text = value.strip()
    return text or None


def _missing(key: str) -> str:
    raise ValueError(f"{key} fehlt oder ist ungueltig.")
