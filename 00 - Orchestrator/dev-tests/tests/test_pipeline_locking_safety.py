from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator.locking import FileLock
from orchestrator.models import DocumentRecord
from orchestrator.pipeline import OrchestratorBusyError, OrchestratorCancelled, OrchestratorEngine
import orchestrator.pipeline.artifact_repository as artifact_repository
import orchestrator.pipeline.bundle_repository as bundle_repository
import orchestrator.pipeline.record_repository as record_repository
import orchestrator.pipeline.storage_repository as storage_repository
from tests.pipeline_fake_modules import FakeModules
from tests.pipeline_harness import create_source, error_root, lock_path, make_engine, make_ui_state, route_root, sha256


@pytest.mark.parametrize("action", ["run", "reset"])
def test_mutations_fail_fast_while_lock_is_held(tmp_path: Path, action: str) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    engine = make_engine(tmp_path, scenarios={})

    with FileLock(lock_path(tmp_path)):
        with pytest.raises(OrchestratorBusyError):
            if action == "run":
                engine.run(ui_state)
            else:
                engine.reset_run_history(ui_state)


def test_run_releases_lock_after_success(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    make_engine(tmp_path, scenarios={}).run(ui_state)

    with FileLock(lock_path(tmp_path)):
        pass


def test_run_releases_lock_after_cancellation(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    engine = OrchestratorEngine(orchestrator_root=tmp_path / "orchestrator", modules=FakeModules({}), cancel_requested=lambda: True)

    with pytest.raises(OrchestratorCancelled):
        engine.run(ui_state)
    with FileLock(lock_path(tmp_path)):
        pass


def test_run_releases_lock_after_unexpected_exception(tmp_path: Path, monkeypatch) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    engine = make_engine(tmp_path, scenarios={})

    def explode(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(record_repository, "discover_input_records", explode)

    with pytest.raises(RuntimeError, match="boom"):
        engine.run(ui_state)
    with FileLock(lock_path(tmp_path)):
        pass


def test_remove_file_prunes_only_within_managed_root(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    engine = make_engine(tmp_path, scenarios={})
    optimizer_root = route_root(ui_state)
    artifact = optimizer_root / "structured" / "doc.structured.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("{}", encoding="utf-8")

    artifact_repository.remove_file(engine, artifact, allowed_roots=(optimizer_root.resolve(),))

    assert not artifact.exists()
    assert optimizer_root.exists()
    assert optimizer_root.parent.exists()


def test_move_source_into_bundle_makes_error_bundle_original_canonical(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    source = create_source(ui_state)
    record = DocumentRecord(content_hash=sha256(source), file_name="doc.pdf", relative_path="doc.pdf", original_source_path=str(source), source_path=str(source))
    engine = make_engine(tmp_path, scenarios={})
    bundle_dir = error_root(ui_state) / "Interpreter" / "Documents"
    collision = bundle_dir / "originals" / "doc.pdf"
    collision.mkdir(parents=True, exist_ok=True)
    (collision / "stale.txt").write_text("stale", encoding="utf-8")

    target = bundle_repository.move_source_into_bundle(engine, record, bundle_dir, allowed_roots=storage_repository.managed_roots(engine, ui_state))

    assert target == bundle_dir / "originals" / "doc.pdf"
    assert target.is_file()
    assert target.read_text(encoding="utf-8") == "doc"
    assert not source.exists()

