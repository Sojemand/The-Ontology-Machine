from __future__ import annotations

import json
from pathlib import Path
import threading

from orchestrator.pipeline import OrchestratorEngine
from tests.pipeline_downstream_stage_fakes import generate_embeddings as fake_generate_embeddings
from tests.pipeline_fake_modules import FakeModules
from tests.pipeline_harness import create_source, make_ui_state


def test_stage_scheduler_advances_second_file_while_first_waits_in_finalizer(tmp_path: Path) -> None:
    class PipelinedModules(FakeModules):
        def __init__(self) -> None:
            super().__init__({})
            self.embedding_started = threading.Event()
            self.allow_embeddings_finish = threading.Event()
            self.second_interpret_done = threading.Event()

        def interpret_document(self, input_path: Path, output_path: Path, **kwargs):
            result = super().interpret_document(input_path, output_path, **kwargs)
            payload = json.loads(input_path.read_text(encoding="utf-8"))
            source = payload.get("source", {}) if isinstance(payload, dict) else {}
            if str(source.get("file_name", "")).strip() == "b.pdf":
                self.second_interpret_done.set()
            return result

        def generate_embeddings(self, corpus_db_path: Path, *, force_enable: bool = False):
            if not self.embedding_started.is_set():
                self.embedding_started.set()
                assert self.allow_embeddings_finish.wait(timeout=5.0)
            return fake_generate_embeddings(self, corpus_db_path, force_enable=force_enable)

    ui_state = make_ui_state(tmp_path)
    create_source(ui_state, "a.pdf", content="a")
    create_source(ui_state, "b.pdf", content="b")
    modules = PipelinedModules()
    engine = OrchestratorEngine(orchestrator_root=tmp_path / "orchestrator", modules=modules)
    result_holder: dict[str, object] = {}
    error_holder: list[BaseException] = []

    def run_pipeline() -> None:
        try:
            result_holder["summary"] = engine.run(ui_state)
        except BaseException as exc:  # pragma: no cover - diagnostic guard
            error_holder.append(exc)

    thread = threading.Thread(target=run_pipeline, name="pipeline-runner", daemon=True)
    thread.start()

    assert modules.embedding_started.wait(timeout=5.0)
    assert modules.second_interpret_done.wait(timeout=5.0)
    modules.allow_embeddings_finish.set()
    thread.join(timeout=10.0)

    assert not error_holder
    assert not thread.is_alive()
    summary = result_holder["summary"]
    assert summary.success == 2
