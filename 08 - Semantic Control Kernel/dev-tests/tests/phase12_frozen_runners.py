from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from test_phase11_fakes import (
    confirmation_for,
    final_manifest_for,
    input_files,
    runtime_for as pipeline_runtime_for,
    target_for as pipeline_target_for,
)
from phase12_merge_entry_support import (
    create_artifact_tree,
    runtime_for as merge_runtime_for,
    seed_rebuild_release,
    source as merge_source,
    target_root as merge_target_root,
)
from semantic_control_kernel.workflows.merge.empty_merge import empty_databases_merge_path
from semantic_control_kernel.workflows.merge.entry import database_merge_additive_only
from semantic_control_kernel.workflows.merge.filled_merge import filled_databases_merge_path
from semantic_control_kernel.workflows.merge.source_selection import build_database_merge_selection
from semantic_control_kernel.workflows.pipeline_run.manual import manual_pipeline_run
from semantic_control_kernel.workflows.pipeline_run.reset import reset_database
from semantic_control_kernel.workflows.rebuild.entry import RebuildWorkflowRuntime, database_rebuild_from_artifacts
from phase12_frozen_inventory import FreezeRun

def _run_merge_entry(tmp_path: Path) -> FreezeRun:
    runtime = merge_runtime_for(tmp_path)
    root = merge_target_root(tmp_path, "merge_entry_target")
    execution = database_merge_additive_only(
        runtime=runtime,
        selected_sources=[merge_source(tmp_path, "entry_a"), merge_source(tmp_path, "entry_b")],
        target_artifact_root=root,
        workflow_run_id="wf_freeze_merge_entry",
        merge_run_id="mrg_freeze_merge_entry",
    )
    return FreezeRun(execution=execution, artifact_root=root, adapters=_merge_adapters(runtime))

def _run_empty_merge_route(tmp_path: Path) -> FreezeRun:
    runtime = merge_runtime_for(tmp_path)
    root = merge_target_root(tmp_path, "empty_merge_target")
    selection = build_database_merge_selection(
        selected_sources=[merge_source(tmp_path, "empty_a"), merge_source(tmp_path, "empty_b")],
        target_artifact_root=root,
        selected_by_interaction_id="interaction_freeze_empty_merge",
        merge_run_id="mrg_freeze_empty_merge",
        created_at="2026-05-31T00:00:00Z",
    ).to_dict()
    execution = empty_databases_merge_path(
        runtime=runtime,
        selection=selection,
        workflow_run_id="wf_freeze_empty_merge",
    )
    return FreezeRun(execution=execution, artifact_root=root, adapters=_merge_adapters(runtime))

def _run_filled_merge_route(tmp_path: Path) -> FreezeRun:
    runtime = merge_runtime_for(tmp_path)
    root = merge_target_root(tmp_path, "filled_merge_target")
    selection = build_database_merge_selection(
        selected_sources=[
            merge_source(tmp_path, "filled_a", state="filled"),
            merge_source(tmp_path, "filled_b", state="filled"),
        ],
        target_artifact_root=root,
        selected_by_interaction_id="interaction_freeze_filled_merge",
        merge_run_id="mrg_freeze_filled_merge",
        created_at="2026-05-31T00:00:00Z",
    ).to_dict()
    execution = filled_databases_merge_path(
        runtime=runtime,
        selection=selection,
        workflow_run_id="wf_freeze_filled_merge",
    )
    return FreezeRun(execution=execution, artifact_root=root, adapters=_merge_adapters(runtime))

def _run_rebuild(tmp_path: Path) -> FreezeRun:
    from phase12_merge_entry_support import FakeCorpusAdapter, FakeEmbeddingAdapter, FakeSemanticReleaseAdapter

    root = tmp_path / "Rebuild Artifact Tree"
    create_artifact_tree(root)
    seed_rebuild_release(root)
    corpus = FakeCorpusAdapter()
    semantic = FakeSemanticReleaseAdapter()
    embedding = FakeEmbeddingAdapter()
    runtime = RebuildWorkflowRuntime(
        state_root=tmp_path / "state",
        corpus_adapter=corpus,
        semantic_release_adapter=semantic,
        embedding_adapter=embedding,
    )
    execution = database_rebuild_from_artifacts(
        runtime=runtime,
        artifact_root=root,
        target_database_name="rebuilt",
        workflow_run_id="wf_freeze_rebuild",
        rebuild_run_id="rbd_freeze_rebuild",
        embedding_provider_configured=True,
    )
    return FreezeRun(
        execution=execution,
        artifact_root=root,
        adapters={"corpus": corpus, "semantic": semantic, "embedding": embedding},
    )

def _run_reset(tmp_path: Path) -> FreezeRun:
    target = pipeline_target_for(tmp_path, workflow_run_id="wf_reset_target")
    manifest = final_manifest_for(target, batch_kind="manual_ingest", workflow_run_id="wf_reset_superseded")
    runtime = pipeline_runtime_for(tmp_path)
    execution = reset_database(
        runtime=runtime,
        target=target,
        confirmation=confirmation_for(target, "reset_database"),
        workflow_run_id="wf_freeze_reset",
        batch_manifests=[manifest],
        reresolved_target_identity=target.target_identity,
    )
    return FreezeRun(
        execution=execution,
        artifact_root=Path(target.artifact_root_path),
        adapters={"corpus": runtime.corpus_adapter},
    )

def _run_manual_pipeline(tmp_path: Path) -> FreezeRun:
    target = pipeline_target_for(tmp_path, workflow_run_id="wf_manual_target")
    files = input_files()
    for item in files:
        input_path = Path(target.artifact_root_path) / item["input_relative_path"]
        input_path.parent.mkdir(parents=True, exist_ok=True)
        input_path.write_text(item["content_hash"], encoding="utf-8")
    runtime = pipeline_runtime_for(tmp_path)
    execution = manual_pipeline_run(
        runtime=runtime,
        target=target,
        input_files=files,
        workflow_run_id="wf_freeze_manual_pipeline",
        confirmation=confirmation_for(target, "manual_pipeline_run"),
    )
    return FreezeRun(
        execution=execution,
        artifact_root=Path(target.artifact_root_path),
        adapters={
            "batch": runtime.batch_adapter,
            "orchestrator": runtime.orchestrator_adapter,
            "corpus": runtime.corpus_adapter,
        },
    )

def _merge_adapters(runtime: Any) -> dict[str, Any]:
    return {
        "workspace": runtime.workspace_adapter,
        "corpus": runtime.corpus_adapter,
        "merge": runtime.merge_adapter,
        "semantic": runtime.semantic_release_adapter,
    }

_RUNNERS: dict[str, Callable[[Path], FreezeRun]] = {
    "database_merge_additive_only": _run_merge_entry,
    "empty_databases_merge_path": _run_empty_merge_route,
    "filled_databases_merge_path": _run_filled_merge_route,
    "database_rebuild_from_artifacts": _run_rebuild,
    "reset_database": _run_reset,
    "manual_pipeline_run": _run_manual_pipeline,
}
