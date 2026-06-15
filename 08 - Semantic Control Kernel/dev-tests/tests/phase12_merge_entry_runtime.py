from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.workflows.merge.entry import MergeWorkflowRuntime

from phase12_merge_entry_merge_adapter import FakeMergeAdapter
from phase12_merge_entry_semantic_adapter import FakeSemanticReleaseAdapter
from phase12_merge_entry_workspace_corpus import FakeCorpusAdapter, FakeWorkspaceAdapter

def runtime_for(tmp_path: Path, *, merge_adapter: FakeMergeAdapter | None = None, semantic_adapter: FakeSemanticReleaseAdapter | None = None, corpus_adapter: FakeCorpusAdapter | None = None):
    return MergeWorkflowRuntime(
        state_root=tmp_path / "state",
        workspace_adapter=FakeWorkspaceAdapter(),
        corpus_adapter=corpus_adapter or FakeCorpusAdapter(),
        semantic_release_adapter=semantic_adapter or FakeSemanticReleaseAdapter(),
        merge_adapter=merge_adapter or FakeMergeAdapter(),
    )
