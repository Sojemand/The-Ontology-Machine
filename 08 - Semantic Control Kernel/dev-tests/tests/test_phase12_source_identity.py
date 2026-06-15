from __future__ import annotations

from phase12_merge_entry_support import source

from semantic_control_kernel.workflows.merge.source_identity import build_source_descriptor, selection_sources_stable
from semantic_control_kernel.workflows.merge.source_selection import build_database_merge_selection


def test_durable_source_id_is_reused(tmp_path) -> None:
    descriptor = build_source_descriptor(source(tmp_path, "a", durable=True), ordinal=1, selection_timestamp="2026-05-06T01:00:00Z")

    assert descriptor.source_database_id == "source_db_a"
    assert descriptor.source_identity_origin == "durable_owner_id"


def test_import_local_id_is_assigned_for_source_without_durable_id(tmp_path) -> None:
    descriptor = build_source_descriptor(source(tmp_path, "a", durable=False), ordinal=1, selection_timestamp="2026-05-06T01:00:00Z")

    assert descriptor.source_database_id.startswith("src_1_")
    assert descriptor.source_identity_origin == "kernel_import_local_id"


def test_import_local_id_is_stable_for_resume_selection(tmp_path) -> None:
    selected = [source(tmp_path, "a", durable=False), source(tmp_path, "b", durable=False)]
    first = build_database_merge_selection(
        selected_sources=selected,
        target_artifact_root=tmp_path / "target",
        selected_by_interaction_id="interaction",
        merge_run_id="merge_stable",
        created_at="2026-05-06T01:00:00Z",
    ).to_dict()
    second = build_database_merge_selection(
        selected_sources=selected,
        target_artifact_root=tmp_path / "target",
        selected_by_interaction_id="interaction",
        merge_run_id="merge_stable",
        created_at="2026-05-06T01:00:00Z",
    ).to_dict()

    assert first["source_databases"][0]["source_database_id"] == second["source_databases"][0]["source_database_id"]
    assert selection_sources_stable(first, second)


def test_stale_selection_is_rejected_when_source_state_changes(tmp_path) -> None:
    first = build_database_merge_selection(
        selected_sources=[source(tmp_path, "a", state="empty"), source(tmp_path, "b", state="empty")],
        target_artifact_root=tmp_path / "target",
        selected_by_interaction_id="interaction",
        created_at="2026-05-06T01:00:00Z",
    ).to_dict()
    changed = build_database_merge_selection(
        selected_sources=[source(tmp_path, "a", state="filled"), source(tmp_path, "b", state="filled")],
        target_artifact_root=tmp_path / "target2",
        selected_by_interaction_id="interaction",
        created_at="2026-05-06T01:00:00Z",
    ).to_dict()

    assert not selection_sources_stable(first, changed)
