"""Rebuild artifact contract handlers."""

from __future__ import annotations

from ..services import create_and_rebuild_new_corpus_db
from ..semantic_release.multi_source_merge_types import path_hash
from ..standalone_artifacts import build_rebuild_bundles_from_artifacts, rebuild_corpus_from_artifacts
from .result_envelope import build_result, kv_artifacts


def handle_preview_rebuild(command, *, context, build_rebuild_bundles_from_artifacts_fn=build_rebuild_bundles_from_artifacts):
    detail = build_rebuild_bundles_from_artifacts_fn(
        context,
        pipeline_root=command.pipeline_root,
        normalized_dir=command.normalized_dir,
        structured_dir=command.structured_dir,
        validation_dir=command.validation_dir,
        raw_dir=getattr(command, "raw_dir", None),
        corpus_db_path=command.corpus_db_path,
    )
    return build_result(
        headline="Rebuild preview completed",
        summary_lines=[f"Bundles: {detail.get('bundle_count', 0)}", f"Missing validation: {detail.get('missing_validation_count', 0)}"],
        artifacts=_rebuild_artifacts(detail),
        detail=_rebuild_detail(detail),
    )


def handle_rebuild(command, *, context, rebuild_corpus_from_artifacts_fn=rebuild_corpus_from_artifacts):
    detail = rebuild_corpus_from_artifacts_fn(
        context,
        pipeline_root=command.pipeline_root,
        normalized_dir=command.normalized_dir,
        structured_dir=command.structured_dir,
        validation_dir=command.validation_dir,
        raw_dir=getattr(command, "raw_dir", None),
        corpus_db_path=command.corpus_db_path,
        release_path=getattr(command, "release_path", None),
        replace_existing=command.replace_existing,
    )
    counts = _load_counts(detail)
    response = build_result(
        headline="Corpus rebuild completed",
        summary_lines=[f"Loaded: {counts['loaded']}", f"Errors: {counts['errors']}"],
        artifacts=_rebuild_artifacts(detail)
        + kv_artifacts(
            [
                ("Active Release", detail.get("active_release_id")),
                ("Corpus DB", detail.get("corpus_db_path")),
                ("Replaced Existing", detail.get("replaced_existing")),
            ]
        ),
        detail={
            **_rebuild_detail(detail),
            "result": counts,
            "active_release_id": detail.get("active_release_id"),
            "active_release_version": detail.get("active_release_version"),
            "active_release_path": detail.get("active_release_path"),
            "active_release_fingerprint": detail.get("active_release_fingerprint"),
            "corpus_db_path": detail.get("corpus_db_path"),
            "release_fingerprint": detail.get("release_fingerprint"),
            "replace_existing": detail.get("replace_existing"),
            "replaced_existing": detail.get("replaced_existing"),
        },
    )
    return _with_target_identity_proof(response, detail)


def handle_create_and_rebuild_new_corpus_db(
    command,
    *,
    context,
    create_and_rebuild_new_corpus_db_fn=create_and_rebuild_new_corpus_db,
    rebuild_corpus_from_artifacts_fn=rebuild_corpus_from_artifacts,
):
    detail = create_and_rebuild_new_corpus_db_fn(
        context,
        confirmation_artifact_path=command.confirmation_artifact_path,
        rebuild_fn=rebuild_corpus_from_artifacts_fn,
        pipeline_root=command.pipeline_root,
        normalized_dir=command.normalized_dir,
        structured_dir=command.structured_dir,
        validation_dir=command.validation_dir,
        raw_dir=getattr(command, "raw_dir", None),
        release_path=getattr(command, "release_path", None),
    )
    counts = _load_counts(detail)
    response = build_result(
        headline="New corpus DB created and rebuilt",
        summary_lines=[f"Loaded: {counts['loaded']}", f"Errors: {counts['errors']}", f"Taxonomy locale: {detail.get('taxonomy_locale') or ''}"],
        artifacts=_rebuild_artifacts(detail)
        + kv_artifacts(
            [
                ("Corpus Root", detail.get("corpus_root")),
                ("Corpus DB", detail.get("corpus_db_path")),
                ("Detached Previous DB", detail.get("previous_default_corpus_db_path")),
            ]
        ),
        detail={
            **_rebuild_detail(detail),
            "result": counts,
            "active_release_id": detail.get("active_release_id"),
            "active_release_version": detail.get("active_release_version"),
            "active_release_path": detail.get("active_release_path"),
            "active_release_fingerprint": detail.get("active_release_fingerprint"),
            "corpus_db_path": detail.get("corpus_db_path"),
            "release_fingerprint": detail.get("release_fingerprint"),
            "replace_existing": False,
            "replaced_existing": False,
            "taxonomy_locale": detail.get("taxonomy_locale"),
            "previous_default_corpus_db_path": detail.get("previous_default_corpus_db_path"),
        },
    )
    return _with_target_identity_proof(response, detail)


def _load_counts(detail: dict) -> dict[str, int]:
    result = detail.get("result")
    return {
        "loaded": getattr(result, "loaded", 0),
        "skipped": getattr(result, "skipped", 0),
        "archived": getattr(result, "archived", 0),
        "errors": getattr(result, "errors", 0),
    }


def _rebuild_artifacts(detail: dict) -> list[dict]:
    return kv_artifacts(
        [
            ("Pipeline Root", detail.get("pipeline_root")),
            ("Normalized Dir", detail.get("normalized_dir")),
            ("Structured Dir", detail.get("structured_dir")),
            ("Validation Dir", detail.get("validation_dir")),
            ("Raw Dir", detail.get("raw_dir")),
            ("Bundle Count", detail.get("bundle_count")),
        ]
    )


def _rebuild_detail(detail: dict) -> dict:
    return {
        "pipeline_root": detail.get("pipeline_root"),
        "artifact_roots": detail.get("artifact_roots"),
        "normalized_dir": detail.get("normalized_dir"),
        "structured_dir": detail.get("structured_dir"),
        "validation_dir": detail.get("validation_dir"),
        "raw_dir": detail.get("raw_dir"),
        "bundle_count": detail.get("bundle_count"),
        "missing_structured_count": detail.get("missing_structured_count"),
        "missing_validation_count": detail.get("missing_validation_count"),
        "missing_raw_count": detail.get("missing_raw_count"),
        "invalid_projection_files": detail.get("invalid_projection_files"),
        "projection_preview": detail.get("projection_preview"),
    }


def _with_target_identity_proof(response: dict, detail: dict) -> dict:
    database_path = str(detail.get("corpus_db_path") or "")
    artifact_root_path = _primary_artifact_root(detail)
    proof = {}
    if database_path:
        proof["database_path"] = database_path
        proof["database_path_hash"] = path_hash(database_path)
    if artifact_root_path:
        proof["artifact_root_path"] = artifact_root_path
        proof["artifact_root_path_hash"] = path_hash(artifact_root_path)
    response["target_identity_proof"] = proof
    if isinstance(response.get("detail"), dict):
        response["detail"].setdefault("database_path", database_path)
        response["detail"].setdefault("artifact_root_path", artifact_root_path)
        if database_path:
            response["detail"].setdefault("database_path_hash", proof["database_path_hash"])
        if artifact_root_path:
            response["detail"].setdefault("artifact_root_path_hash", proof["artifact_root_path_hash"])
    return response


def _primary_artifact_root(detail: dict) -> str:
    pipeline_root = str(detail.get("pipeline_root") or "")
    if pipeline_root:
        return pipeline_root
    artifact_roots = detail.get("artifact_roots")
    if isinstance(artifact_roots, list) and artifact_roots:
        return str(artifact_roots[0] or "")
    return ""
