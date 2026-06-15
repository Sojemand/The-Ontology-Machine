from __future__ import annotations

import json
from pathlib import Path

from orchestrator.integrations import (
    CorpusLoadStageResult,
    EmbeddingStageResult,
    ExternalDependencyStatus,
    ModuleHealthStatus,
    NormalizationStageResult,
)

from .pipeline_request_fixture_support import write_normalizer_request_fixture


def normalize_document(
    module,
    structured_path: Path,
    normalized_output_path: Path,
    *,
    request_output_path: Path | None = None,
    release: dict[str, object] | None = None,
) -> NormalizationStageResult:
    module.normalized_paths.append(str(structured_path))
    module.normalizer_release_fingerprints.append(
        str(release.get("fingerprint") or "") if isinstance(release, dict) else ""
    )
    name = module.name_for_structured(structured_path)
    outcome = module.next_outcome(name, "normalize", {"status": "OK"})
    if outcome["status"] == "ERROR":
        return NormalizationStageResult(status="ERROR", error=str(outcome.get("error", "normalize failed")))
    default_output = normalized_output_path
    normalized_path_text = str(outcome["output_path"]) if "output_path" in outcome else str(default_output)
    normalized_path = Path(normalized_path_text) if normalized_path_text else None
    payload = outcome.get(
        "normalized_payload",
        {
            "schema_version": "1.0",
            "processing": {
                "needs_review": bool(outcome.get("needs_review", False)),
                "review_reason": str(outcome.get("review_reason", outcome.get("message", ""))),
            },
            "classification": {"document_type": "normalized"},
            "context": {"taxonomy_profile_id": "housing.default.v1"},
            "content": {"free_text": "normalized", "fields": {}, "rows": [], "structure": {}},
            "relations": [],
        },
    )
    if outcome.get("create_normalized", True) and normalized_path is not None:
        normalized_path.parent.mkdir(parents=True, exist_ok=True)
        normalized_path.write_text(json.dumps(payload), encoding="utf-8")
    if normalized_path is not None:
        module.normalized_to_name[str(normalized_path)] = name
    request_path_text = write_normalizer_request_fixture(request_output_path, structured_path)
    return NormalizationStageResult(
        status="OK",
        output_path=normalized_path_text,
        request_path=request_path_text,
        needs_review=bool(outcome.get("needs_review", False)),
        message=str(outcome.get("message", "normalized")),
        review_reason=str(outcome.get("review_reason", "")),
    )

def load_document(
    module,
    structured_path: Path,
    validation_path: Path,
    normalized_path: Path,
    raw_path: Path | None,
    corpus_db_path: Path,
    *,
    persist_page_images_in_db: bool | None = None,
    page_images_dir: Path | None = None,
) -> CorpusLoadStageResult:
    module.loaded_paths.append(str(structured_path))
    module.loaded_validation_paths.append(str(validation_path))
    module.loaded_normalized_paths.append(str(normalized_path))
    module.loaded_raw_paths.append(str(raw_path) if raw_path is not None else "")
    module.loaded_page_image_persistence_flags.append(persist_page_images_in_db)
    module.loaded_page_images_dirs.append(str(page_images_dir) if page_images_dir is not None else "")
    name = module.name_for_structured(structured_path)
    outcome = module.next_outcome(name, "load", {"status": "loaded"})
    if outcome["status"] in {"loaded", "archived_and_loaded", "skipped"}:
        corpus_db_path.parent.mkdir(parents=True, exist_ok=True)
        corpus_db_path.touch()
    return CorpusLoadStageResult(status=str(outcome["status"]), reason=str(outcome.get("reason", "")))


def generate_embeddings(module, corpus_db_path: Path, *, force_enable: bool = False) -> EmbeddingStageResult:
    module.embedding_calls.append(str(corpus_db_path))
    module.embedding_force_flags.append(force_enable)
    outcome = module.next_outcome("__embeddings__", "embed", {"status": "completed", "count": 0, "reason": ""})
    raised = outcome.get("raise")
    if isinstance(raised, Exception):
        raise raised
    return EmbeddingStageResult(
        status=str(outcome.get("status", "completed")),
        count=int(outcome.get("count", 0) or 0),
        reason=str(outcome.get("reason", "")),
    )


def healthcheck(
    module,
    *,
    module_keys: tuple[str, ...] | None = None,
    scope: str = "pipeline_run",
    required_dependencies_by_module: dict[str, tuple[str, ...]] | None = None,
    corpus_db_path: Path | None = None,
) -> list[ModuleHealthStatus]:
    module.healthcheck_calls.append((module_keys, scope, required_dependencies_by_module, str(corpus_db_path) if corpus_db_path is not None else ""))
    configured = module.scenarios.get("__healthcheck__", {}).get(scope, [])
    results: list[ModuleHealthStatus] = []
    for item in configured:
        if isinstance(item, ModuleHealthStatus):
            results.append(item)
            continue
        if not isinstance(item, dict):
            continue
        dependencies = [
            ExternalDependencyStatus(
                name=str(dependency.get("name", "")),
                kind=str(dependency.get("kind", "service")),
                required=bool(dependency.get("required", True)),
                healthy=bool(dependency.get("healthy", False)),
                detail=str(dependency.get("detail", "")),
            )
            for dependency in item.get("dependencies", [])
            if isinstance(dependency, dict)
        ]
        results.append(
            ModuleHealthStatus(
                key=str(item.get("key", "")),
                display_name=str(item.get("display_name", item.get("key", ""))),
                healthy=bool(item.get("healthy", True)),
                message=str(item.get("message", "")),
                dependencies=dependencies,
            )
        )
    return results
