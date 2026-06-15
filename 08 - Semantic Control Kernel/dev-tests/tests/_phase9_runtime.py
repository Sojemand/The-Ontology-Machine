from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from semantic_control_kernel.types.database_creation import DatabaseCreationTarget

from _phase9_creation_adapters import FakeCorpusAdapter, FakeInteractionPort, FakeWorkspaceAdapter
from _phase9_llm_fakes import FakeLLMPort
from _phase9_semantic_adapter import FakeSemanticReleaseAdapter


def target_for(tmp_path: Path, *, name: str = "Artifact Tree", database_name: str = "kernel_test") -> DatabaseCreationTarget:
    return DatabaseCreationTarget.from_selection(
        artifact_root_parent=tmp_path,
        artifact_root_name=name,
        database_name=database_name,
    )


def sample_refs_for(target: DatabaseCreationTarget, *, prefix: str = "sample", count: int = 2) -> tuple[Mapping[str, Any], ...]:
    refs = []
    for index in range(count):
        sample_id = f"{prefix}_{index}"
        refs.append(
            {
                "sample_id": sample_id,
                "path": str(Path(target.input_path) / f"{sample_id}.json"),
                "analyze_sample_input": {
                    "schema_version": "kernel.analyze_sample.input.v1",
                    "sample_id": sample_id,
                    "source_ref": {"kind": "interpreter_request_view_file.v1"},
                    "route": {"profile": "file"},
                    "document": {
                        "artifact_path": f"Input/{sample_id}.json",
                        "title": f"{prefix.title()} {index}",
                    },
                    "completeness": {"status": "complete"},
                },
            }
        )
    return tuple(refs)


def runtime_for(
    tmp_path: Path,
    *,
    target: DatabaseCreationTarget | None = None,
    semantic_adapter: FakeSemanticReleaseAdapter | None = None,
    workspace_adapter: FakeWorkspaceAdapter | None = None,
    llm_port: FakeLLMPort | None = None,
    taxonomy_samples: Sequence[Mapping[str, Any]] = (),
    projection_samples: Sequence[Mapping[str, Any]] = (),
    taxonomy_ref: Mapping[str, Any] | None = None,
):
    from semantic_control_kernel.workflows.database_creation.routes import DatabaseCreationRuntime

    return DatabaseCreationRuntime(
        state_root=tmp_path / "state",
        workspace_adapter=workspace_adapter or FakeWorkspaceAdapter(),
        corpus_adapter=FakeCorpusAdapter(),
        semantic_release_adapter=semantic_adapter or FakeSemanticReleaseAdapter(),
        interaction_port=FakeInteractionPort(
            target=target,
            taxonomy_samples=taxonomy_samples,
            projection_samples=projection_samples,
            taxonomy_ref=taxonomy_ref,
        ),
        llm_port=llm_port,
        blueprint_ref="default-blueprint",
    )
