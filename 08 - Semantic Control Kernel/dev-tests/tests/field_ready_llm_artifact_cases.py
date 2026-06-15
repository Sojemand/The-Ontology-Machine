from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from semantic_control_kernel.repository import atomic_json as atomic_module
from semantic_control_kernel.workflows.llm_calls.artifacts import LLMArtifactStore
from semantic_control_kernel.workflows.llm_calls.function_registry import get_llm_function_definition


def test_llm_artifacts_publish_via_atomic_replace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    replace_calls: list[tuple[Path, Path]] = []
    original_replace = os.replace

    def capture_replace(src, dst):
        replace_calls.append((Path(src), Path(dst)))
        return original_replace(src, dst)

    monkeypatch.setattr(atomic_module.os, "replace", capture_replace)
    target = tmp_path / "llm" / "prompt_snapshot.json"

    LLMArtifactStore(tmp_path).write_json(target, {"schema_version": "probe.v1"})

    assert target.read_text(encoding="utf-8").endswith("\n")
    assert any(dst == target and src != target for src, dst in replace_calls)


def test_llm_artifact_json_preserves_existing_target_when_temp_write_is_partial(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "llm" / "parsed_output.json"
    target.parent.mkdir(parents=True)
    target.write_text('{"status":"original"}\n', encoding="utf-8")
    original_write_text = Path.write_text

    def partial_temp_write(self, *args, **kwargs):
        if self.name.endswith(".tmp"):
            original_write_text(self, "{partial", encoding="utf-8")
            raise OSError("simulated interrupted temp write")
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", partial_temp_write)

    with pytest.raises(OSError):
        LLMArtifactStore(tmp_path).write_json(target, {"status": "replacement"})

    assert target.read_text(encoding="utf-8") == '{"status":"original"}\n'
    assert not list(target.parent.glob("*.tmp"))


def test_llm_artifact_text_preserves_existing_target_when_temp_write_is_partial(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "llm" / "report.md"
    target.parent.mkdir(parents=True)
    target.write_text("original\n", encoding="utf-8")
    original_write_text = Path.write_text

    def partial_temp_write(self, *args, **kwargs):
        if self.name.endswith(".tmp"):
            original_write_text(self, "partial", encoding="utf-8")
            raise OSError("simulated interrupted temp write")
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", partial_temp_write)

    with pytest.raises(OSError):
        LLMArtifactStore(tmp_path).write_text(target, "replacement\n")

    assert target.read_text(encoding="utf-8") == "original\n"
    assert not list(target.parent.glob("*.tmp"))


def test_llm_sample_input_artifacts_handle_legacy_windows_long_paths(tmp_path: Path) -> None:
    if os.name != "nt":
        pytest.skip("legacy Windows path handling is Windows-specific")

    artifact_root = tmp_path / "Semantic Release"
    analysis_run_id = "wr_20260602T175610323310Z_f11f7655232b_taxonomy"
    sample_id = "11_pdfsam_bewusstseinsreisen_version_2_f2f1adff"
    target = (
        artifact_root
        / "sa"
        / analysis_run_id
        / "in"
        / sample_id
        / "input.json"
    )
    segment = 0
    while len(str(target)) < 270:
        artifact_root = artifact_root / f"deep_segment_{segment:02d}"
        target = (
            artifact_root
            / "sa"
            / analysis_run_id
            / "in"
            / sample_id
            / "input.json"
        )
        segment += 1

    definition = get_llm_function_definition("analyze_samples")
    bindings = LLMArtifactStore(artifact_root).write_input_artifacts(
        definition,
        analysis_run_id,
        [
            {
                "schema_version": "kernel.analyze_sample.input.v1",
                "sample_id": sample_id,
                "source_ref": {"path": "sample.pdf"},
                "route": {"route_id": "sample"},
                "document": {"title": "Sample"},
                "completeness": {"status": "sample"},
            }
        ],
    )

    assert bindings["{{kernel_analyze_sample_inputs_json}}"].endswith("/in")
    assert len(str(target)) >= 270
    assert json.loads(read_long_path_text(target))["sample_id"] == sample_id


def read_long_path_text(path: Path) -> str:
    if os.name == "nt" and len(str(path)) >= 240:
        return Path("\\\\?\\" + str(path)).read_text(encoding="utf-8")
    return path.read_text(encoding="utf-8")
