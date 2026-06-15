from __future__ import annotations

import json
from pathlib import Path

from orchestrator.integrations import PipelineModules

from support.pipeline_fake_semantic_impl import PipelineFakeSemanticMixin
from support.pipeline_fake_stage_impl import PipelineFakeStageMixin


class FakeModules(PipelineFakeStageMixin, PipelineFakeSemanticMixin, PipelineModules):
    def __init__(self, scenarios: dict[str, dict[str, object]]) -> None:
        self.scenarios = scenarios
        self.structured_to_name: dict[str, str] = {}
        self.structured_name_by_filename: dict[str, str] = {}
        self.normalized_to_name: dict[str, str] = {}
        self.embedding_calls: list[str] = []
        self.embedding_force_flags: list[bool] = []
        self.validated_paths: list[str] = []
        self.validator_raw_paths: list[str] = []
        self.normalized_paths: list[str] = []
        self.loaded_paths: list[str] = []
        self.loaded_validation_paths: list[str] = []
        self.loaded_normalized_paths: list[str] = []
        self.loaded_raw_paths: list[str] = []
        self.loaded_page_image_persistence_flags: list[bool | None] = []
        self.loaded_page_images_dirs: list[str] = []
        self.healthcheck_calls: list[tuple[tuple[str, ...] | None, str, dict[str, tuple[str, ...]] | None, str]] = []
        self.extract_calls: list[dict[str, str]] = []
        self.interpret_calls: list[str] = []
        self.runtime_semantic_release_reads: list[str] = []
        self.runtime_semantic_asset_builds: list[str] = []
        self.normalizer_release_fingerprints: list[str] = []
        self.release_preflight_calls: list[tuple[str, str]] = []

    def close(self) -> None:
        return None

    def next_outcome(self, name: str, stage: str, default: dict[str, object]) -> dict[str, object]:
        stage_map = self.scenarios.setdefault(name, {})
        value = stage_map.get(stage, default)
        if isinstance(value, list):
            if len(value) > 1:
                return dict(value.pop(0))
            return dict(value[0])
        return dict(value)

    def name_for_structured(self, structured_path: Path) -> str:
        mapped = self.structured_to_name.get(str(structured_path))
        if mapped:
            return mapped
        mapped = self.structured_name_by_filename.get(structured_path.name)
        if mapped:
            return mapped
        payload = json.loads(structured_path.read_text(encoding="utf-8"))
        source = payload.get("source", {}) if isinstance(payload, dict) else {}
        name = str(source.get("file_name", "")).strip()
        if not name:
            raise KeyError(structured_path.name)
        if structured_path.name != "structured.json":
            self.structured_name_by_filename[structured_path.name] = name
        return name
