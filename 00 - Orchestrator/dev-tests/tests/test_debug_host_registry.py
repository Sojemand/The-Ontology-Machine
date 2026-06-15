from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchestrator.debug_host import registry
from tests.debug_host_test_support import write_debug_registry

MODULE_ROOT = Path(__file__).resolve().parents[2]
REAL_REGISTRY_PATH = MODULE_ROOT / "module-registry.json"


def test_descriptor_and_plans_come_from_module_manifest(tmp_path: Path) -> None:
    registry_path = write_debug_registry(
        tmp_path,
        include_validator=True,
        include_normalizer=True,
        include_interpreter=True,
        include_corpus_builder=True,
    )
    descriptors = registry.available_descriptors(registry_path=registry_path)

    descriptor = registry.descriptor_for("optimizer", registry_path=registry_path)
    scan_plan = registry.plan_for("optimizer", "scan", registry_path=registry_path)
    single_plan = registry.plan_for("optimizer", "single", registry_path=registry_path)
    interpreter = registry.descriptor_for("interpreter", registry_path=registry_path)
    interpreter_scan_plan = registry.plan_for("interpreter", "scan", registry_path=registry_path)
    interpreter_plan = registry.plan_for("interpreter", "single", registry_path=registry_path)
    interpreter_batch_plan = registry.plan_for("interpreter", "batch", registry_path=registry_path)
    validator = registry.descriptor_for("validator", registry_path=registry_path)
    validator_batch_plan = registry.plan_for("validator", "batch", registry_path=registry_path)
    normalizer = registry.descriptor_for("normalizer", registry_path=registry_path)
    normalizer_single_plan = registry.plan_for("normalizer", "single", registry_path=registry_path)
    normalizer_batch_plan = registry.plan_for("normalizer", "batch", registry_path=registry_path)
    corpus_builder = registry.descriptor_for("corpus_builder", registry_path=registry_path)
    corpus_builder_scan_plan = registry.plan_for("corpus_builder", "scan", registry_path=registry_path)
    corpus_builder_single_plan = registry.plan_for("corpus_builder", "single", registry_path=registry_path)
    corpus_builder_batch_plan = registry.plan_for("corpus_builder", "batch", registry_path=registry_path)

    assert tuple(sorted(descriptors)) == ("corpus_builder", "interpreter", "normalizer", "optimizer", "validator")
    assert descriptor.stage_role == "Optimizer"
    assert descriptor.controls == ("mode", "filters", "worker_count", "hash_tools")
    assert interpreter.stage_role == "Interpreter"
    assert interpreter.controls == ()
    assert validator.stage_role == "Validator"
    assert validator.controls == ("mode", "raw_evidence", "check_toggles")
    assert validator.input_source == "module_selected_input"
    assert normalizer.stage_role == "Normalizer"
    assert normalizer.controls == ("mode", "worker_count")
    assert normalizer.input_source == "module_selected_input"
    assert corpus_builder.stage_role == "Corpus Builder"
    assert corpus_builder.controls == ("mode", "persist_page_images")
    assert corpus_builder.artifacts == ("corpus_db", "preview_report", "load_report")
    assert corpus_builder.input_source == "module_selected_input"
    assert scan_plan.steps[0].action == "scan_debug_input"
    assert single_plan.steps[0].action == "debug_run"
    assert tuple(step.label for step in validator_batch_plan.steps) == ("validator:debug_run",)
    assert tuple(step.label for step in normalizer_single_plan.steps) == ("normalizer:debug_run",)
    assert tuple(step.label for step in normalizer_batch_plan.steps) == ("normalizer:debug_run",)
    assert tuple(step.label for step in corpus_builder_scan_plan.steps) == ("corpus_builder:scan_debug_input",)
    assert tuple(step.label for step in corpus_builder_single_plan.steps) == ("corpus_builder:debug_run",)
    assert tuple(step.label for step in corpus_builder_batch_plan.steps) == ("corpus_builder:debug_run",)
    assert tuple(step.label for step in interpreter_plan.steps) == (
        "optimizer:debug_run",
        "request_enrichment",
        "interpreter:debug_run",
    )
    assert tuple(step.label for step in interpreter_scan_plan.steps) == ("optimizer:scan_debug_input",)
    assert tuple(step.label for step in interpreter_batch_plan.steps) == (
        "optimizer:debug_run",
        "request_enrichment",
        "interpreter:debug_run",
    )


def test_descriptor_rejects_unknown_control_tokens(tmp_path: Path) -> None:
    registry_path = write_debug_registry(tmp_path, controls=("mode", "filters", "worker_count", "local_ui_magic"))

    with pytest.raises(ValueError, match="Unknown debug_surface.controls"):
        registry.descriptor_for("optimizer", registry_path=registry_path)


def test_registry_catalog_is_cached_per_registry_path(tmp_path: Path, monkeypatch) -> None:
    registry_path = write_debug_registry(tmp_path, include_validator=True)
    load_calls: list[Path | None] = []
    original = registry.load_module_registry

    def _counted_load(path=None):
        load_calls.append(path)
        return original(path)

    monkeypatch.setattr(registry, "load_module_registry", _counted_load)

    first = registry.available_descriptors(registry_path=registry_path)
    second = registry.available_descriptors(registry_path=registry_path)
    descriptor = registry.descriptor_for("validator", registry_path=registry_path)
    plan = registry.plan_for("validator", "batch", registry_path=registry_path)

    assert first == second
    assert descriptor.module_key == "validator"
    assert tuple(step.label for step in plan.steps) == ("validator:debug_run",)
    assert len(load_calls) == 1

