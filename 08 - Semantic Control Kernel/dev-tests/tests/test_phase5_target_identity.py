from __future__ import annotations

from semantic_control_kernel.domain.state_machine.identity import build_target_identity


def test_path_hash_normalization_handles_windows_and_posix_forms() -> None:
    windows_a = build_target_identity({"database_path": "C:/Data/Corpus/main.sqlite"})
    windows_b = build_target_identity({"database_path": "c:\\data\\corpus\\main.sqlite"})
    posix_a = build_target_identity({"artifact_root_path": "/tmp/artifact-root/"})
    posix_b = build_target_identity({"artifact_root_path": "/tmp/artifact-root"})

    assert windows_a.database_path_hash == windows_b.database_path_hash
    assert posix_a.artifact_root_path_hash == posix_b.artifact_root_path_hash


def test_projection_and_source_database_hashes_are_order_stable() -> None:
    first = build_target_identity(
        {
            "projection_fingerprints": ["proj_b", "proj_a"],
            "source_database_ids": ["db_2", "db_1"],
        }
    )
    second = build_target_identity(
        {
            "projection_fingerprints": ["proj_a", "proj_b"],
            "source_database_ids": ["db_1", "db_2"],
        }
    )

    assert first.projection_set_hash == second.projection_set_hash
    assert first.source_database_set_hash == second.source_database_set_hash


def test_target_hash_never_includes_user_prompt_text() -> None:
    first = build_target_identity({"database_path": "C:/db/main.sqlite", "user_prompt": "please do one thing"})
    second = build_target_identity({"database_path": "C:/db/main.sqlite", "user_prompt": "please do another"})

    assert first.target_hash == second.target_hash
