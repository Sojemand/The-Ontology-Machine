from __future__ import annotations

from pathlib import Path

import pytest

from corpus_builder.database_analysis.workflow import read_database_analysis_evidence
from corpus_builder.orchestrator_contract.validation_suite import parse_read_database_analysis_evidence_command
from corpus_builder.semantic_release.multi_source_merge_types import path_hash

from .database_analysis_evidence_reader_support import artifact_tree, database, owner_request


def test_read_database_analysis_evidence_rejects_unknown_fields() -> None:
    with pytest.raises(ValueError):
        parse_read_database_analysis_evidence_command(
            {
                **owner_request(
                    "read_database_analysis_evidence",
                    database_path="C:/tmp/corpus.db",
                    database_path_hash="sha256:test",
                    artifact_root="C:/tmp",
                    active_release_ref={"release_fingerprint": "fp_release"},
                    release_materialization_refs=[{"artifact_path": "Documents/logs/materialization.json"}],
                    analysis_scope="database_coverage",
                ),
                "unexpected": True,
            }
        )


def test_parse_read_database_analysis_evidence_requires_request_fingerprint() -> None:
    payload = owner_request(
        "read_database_analysis_evidence",
        database_path="C:/tmp/corpus.db",
        database_path_hash="sha256:test",
        artifact_root="C:/tmp",
        active_release_ref={"release_fingerprint": "fp_release"},
        release_materialization_refs=[{"artifact_path": "Documents/logs/materialization.json"}],
        analysis_scope="database_coverage",
    )
    payload.pop("request_fingerprint")

    with pytest.raises(ValueError, match="request_fingerprint"):
        parse_read_database_analysis_evidence_command(payload)  # type: ignore[arg-type]


def test_read_database_analysis_evidence_rejects_missing_materialization_refs(tmp_path: Path) -> None:
    artifact_root = tmp_path / "Artifact Tree"
    artifact_tree(artifact_root)
    db_path = database(artifact_root)

    with pytest.raises(ValueError, match="materialization_refs_missing"):
        read_database_analysis_evidence(
            {
                "database_path": str(db_path),
                "database_path_hash": path_hash(db_path),
                "artifact_root": str(artifact_root),
                "active_release_ref": {"release_id": "release_a", "release_version": "v1", "release_fingerprint": "fp_release"},
                "release_materialization_refs": [],
                "analysis_scope": "database_coverage",
                "target_identity": {
                    "database_path_hash": path_hash(db_path),
                    "artifact_root_path_hash": path_hash(artifact_root),
                    "release_fingerprint": "fp_release",
                },
            }
        )


def test_read_database_analysis_evidence_rejects_release_fingerprint_mismatch(tmp_path: Path) -> None:
    artifact_root = tmp_path / "Artifact Tree"
    artifact_tree(artifact_root)
    db_path = database(artifact_root, active_release_fingerprint="fp_actual")

    with pytest.raises(ValueError, match="release_fingerprint_mismatch"):
        read_database_analysis_evidence(
            {
                "database_path": str(db_path),
                "database_path_hash": path_hash(db_path),
                "artifact_root": str(artifact_root),
                "active_release_ref": {"release_id": "release_a", "release_version": "v1", "release_fingerprint": "fp_expected"},
                "release_materialization_refs": [{"artifact_path": "Documents/logs/materialization.json"}],
                "analysis_scope": "database_coverage",
                "target_identity": {
                    "database_path_hash": path_hash(db_path),
                    "artifact_root_path_hash": path_hash(artifact_root),
                    "release_fingerprint": "fp_expected",
                },
            }
        )
