from __future__ import annotations

import pytest

from semantic_control_kernel.validation.merge_validation import validate_materialization_refs_preserved
from semantic_control_kernel.workflows.merge.id_map import build_id_map, deterministic_target_id

from test_phase12_merge_id_map import _mapping


def test_sql_primary_key_document_record_and_fk_remap_are_deterministic() -> None:
    assert deterministic_target_id("source_db_a", "record_a") == deterministic_target_id("source_db_a", "record_a")


def test_materialization_refs_are_preserved_in_id_map() -> None:
    id_map = build_id_map(
        merge_run_id="merge_sql",
        source_databases=[{"source_database_id": "source_db_a"}],
        target_database_path="C:/target/Corpus/corpus.db",
        mappings=[_mapping()],
    ).to_dict()

    assert validate_materialization_refs_preserved(id_map) is None


def test_incomplete_remap_blocks() -> None:
    with pytest.raises(ValueError, match="projection_id"):
        build_id_map(
            merge_run_id="merge_sql",
            source_databases=[{"source_database_id": "source_db_a"}],
            target_database_path="C:/target/Corpus/corpus.db",
            mappings=[_mapping(projection_id="")],
        )
