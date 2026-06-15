from __future__ import annotations

import os
from pathlib import Path

import pytest

from semantic_control_kernel.repository import atomic_json as atomic_module
from semantic_control_kernel.repository.atomic_json import AtomicJsonStore, atomic_write_text
from semantic_control_kernel.repository.ids import generate_id, require_state_id
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.workflows.merge.receipts import merge_run_dir
from semantic_control_kernel.workflows.merge.source_selection_builder import build_database_merge_selection
from semantic_control_kernel.workflows.rebuild.entry import RebuildWorkflowRuntime, database_rebuild_from_artifacts
from semantic_control_kernel.workflows.rebuild.manifest import write_rebuild_manifest


def _merge_sources() -> list[dict[str, str]]:
    return [
        {
            "source_database_path": r"C:\tmp\a\Corpus\corpus.db",
            "source_artifact_root": r"C:\tmp\a",
            "source_state": "empty",
            "source_semantic_release_id": "rel",
            "source_semantic_release_version": "1",
            "source_release_fingerprint": "sha256:a",
            "source_artifact_tree_fingerprint": "sha256:aa",
        },
        {
            "source_database_path": r"C:\tmp\b\Corpus\corpus.db",
            "source_artifact_root": r"C:\tmp\b",
            "source_state": "empty",
            "source_semantic_release_id": "rel",
            "source_semantic_release_version": "1",
            "source_release_fingerprint": "sha256:b",
            "source_artifact_tree_fingerprint": "sha256:bb",
        },
    ]


def test_atomic_store_temp_name_does_not_extend_final_filename(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    store = AtomicJsonStore(paths, "field_ready")
    final_name = ("very_long_kernel_state_filename_" * 3) + ".json"
    target = paths.safe_path("workflow_runs", "active", final_name)
    replace_sources: list[Path] = []
    original_replace = os.replace

    def capture_replace(src, dst):
        replace_sources.append(Path(src))
        return original_replace(src, dst)

    monkeypatch.setattr(atomic_module.os, "replace", capture_replace)

    store.write_json(target, {"schema_version": "field_ready.v1"})

    state_temp_sources = [path for path in replace_sources if path.parent == paths.tmp_dir]
    assert state_temp_sources
    assert all(final_name not in path.name for path in state_temp_sources)
    assert all(len(path.name) <= 18 for path in state_temp_sources)


def test_atomic_store_temp_path_stays_inside_legacy_windows_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_root = tmp_path / "state"
    index = 0
    while len(str(state_root)) < 190:
        state_root = state_root / f"deep_{index:02d}"
        index += 1
    paths = StatePaths.from_state_root(state_root)
    store = AtomicJsonStore(paths, "field_ready")
    target = paths.safe_path("a.json")
    replace_sources: list[Path] = []
    original_replace = os.replace

    def capture_replace(src, dst):
        replace_sources.append(Path(src))
        return original_replace(src, dst)

    monkeypatch.setattr(atomic_module.os, "replace", capture_replace)

    store.write_json(target, {"schema_version": "field_ready.v1"})

    state_temp_sources = [path for path in replace_sources if path.parent == paths.tmp_dir]
    assert state_temp_sources
    assert len(str(target)) < 260
    assert all(len(str(path)) < 260 for path in state_temp_sources)


def test_state_layout_initial_files_publish_via_shared_atomic_writer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    replace_calls: list[tuple[Path, Path]] = []
    original_replace = os.replace

    def capture_replace(src, dst):
        replace_calls.append((Path(src), Path(dst)))
        return original_replace(src, dst)

    monkeypatch.setattr(atomic_module.os, "replace", capture_replace)

    paths.ensure_layout()

    published = {
        dst.relative_to(paths.state_root).as_posix()
        for _, dst in replace_calls
        if dst.is_relative_to(paths.state_root)
    }
    assert {"README.md", "state_root_manifest.json", "support/index.json"} <= published
    assert all(dst.name not in src.name for src, dst in replace_calls)
    assert all(src.name.startswith(".t") and src.name.endswith(".tmp") for src, _ in replace_calls)
    assert all(len(src.name) <= 18 for src, _ in replace_calls)


def test_workflow_run_id_rejects_overlong_state_filename_before_write(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    overlong_workflow_id = "wr_" + ("x" * 260)

    with pytest.raises(ValueError, match="workflow_run_id"):
        WorkflowRunStore(paths).create_run(
            "manual_pipeline_run",
            {"target_hash": "field_ready_target"},
            "field_ready",
            workflow_run_id=overlong_workflow_id,
        )

    assert list(paths.workflow_runs_active_dir.glob("*.json")) == []


def test_generated_workflow_run_id_stays_short_for_state_paths(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    run = WorkflowRunStore(paths).create_run("manual_pipeline_run", {"target_hash": "short_id_target"}, "field_ready")

    assert run.workflow_run_id.startswith("wr_")
    assert len(run.workflow_run_id) <= 24
    assert "T" not in run.workflow_run_id
    assert require_state_id("workflow_run_id", run.workflow_run_id) == run.workflow_run_id
    assert (paths.workflow_runs_active_dir / f"{run.workflow_run_id}.json").is_file()


def test_generated_kernel_ids_use_short_random_tokens() -> None:
    workflow_id = generate_id("workflow_run_id")
    support_id = generate_id("support_bundle_id")

    assert workflow_id.startswith("wr_")
    assert support_id.startswith("spt_")
    assert len(workflow_id) <= 24
    assert len(support_id) <= 24
    assert "T" not in workflow_id
    assert "T" not in support_id


def test_merge_run_id_rejects_overlong_artifact_log_component_before_write(tmp_path: Path) -> None:
    target_root = tmp_path / "target"
    overlong_merge_id = "mrg_" + ("x" * 260)

    with pytest.raises(ValueError, match="merge_run_id"):
        build_database_merge_selection(
            selected_sources=_merge_sources(),
            target_artifact_root=target_root,
            selected_by_interaction_id="irq_field_ready",
            merge_run_id=overlong_merge_id,
        )
    with pytest.raises(ValueError, match="merge_run_id"):
        merge_run_dir(target_root, overlong_merge_id)

    assert not (target_root / "Documents").exists()


def test_rebuild_run_id_rejects_overlong_artifact_log_component_before_write(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifact"
    overlong_rebuild_id = "rbd_" + ("x" * 260)
    runtime = RebuildWorkflowRuntime(
        state_root=tmp_path / "state",
        corpus_adapter=object(),
        semantic_release_adapter=object(),
        embedding_adapter=object(),
    )

    with pytest.raises(ValueError, match="rebuild_run_id"):
        database_rebuild_from_artifacts(
            runtime=runtime,
            artifact_root=artifact_root,
            target_database_name="rebuilt",
            rebuild_run_id=overlong_rebuild_id,
        )
    with pytest.raises(ValueError, match="rebuild_run_id"):
        write_rebuild_manifest(artifact_root, overlong_rebuild_id, {"schema_version": "probe"})

    assert not (artifact_root / "Documents").exists()
    assert not (tmp_path / "state").exists()


def test_atomic_write_text_preserves_existing_target_when_temp_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "contract_response.json"
    target.write_text("original\n", encoding="utf-8")
    original_write_text = Path.write_text

    def fail_temp_write(self, *args, **kwargs):
        if self.name.endswith(".tmp"):
            raise OSError("simulated temp write failure")
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_temp_write)

    with pytest.raises(OSError):
        atomic_write_text(target, "replacement\n")

    assert target.read_text(encoding="utf-8") == "original\n"
    assert not list(tmp_path.glob("*.tmp"))
