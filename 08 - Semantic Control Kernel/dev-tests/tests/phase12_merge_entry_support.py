from __future__ import annotations

from semantic_control_kernel.workflows.merge.entry import database_merge_additive_only
from semantic_control_kernel.workflows.merge.source_selection import build_database_merge_selection

from phase12_merge_entry_embedding_adapter import FakeEmbeddingAdapter
from phase12_merge_entry_fixtures import (
    create_artifact_tree,
    merge_resolution,
    merge_target_confirmation,
    reconciliation_receipt,
    seed_rebuild_release,
    source,
    target_root,
    write_release_package,
)
from phase12_merge_entry_merge_adapter import FakeMergeAdapter
from phase12_merge_entry_results import ok_result, owner_error
from phase12_merge_entry_runtime import runtime_for
from phase12_merge_entry_semantic_adapter import FakeSemanticReleaseAdapter
from phase12_merge_entry_workspace_corpus import FakeCorpusAdapter

__all__ = [
    "FakeCorpusAdapter",
    "FakeEmbeddingAdapter",
    "FakeMergeAdapter",
    "FakeSemanticReleaseAdapter",
    "build_database_merge_selection",
    "create_artifact_tree",
    "database_merge_additive_only",
    "merge_resolution",
    "merge_target_confirmation",
    "ok_result",
    "owner_error",
    "reconciliation_receipt",
    "runtime_for",
    "seed_rebuild_release",
    "source",
    "target_root",
    "write_release_package",
]
