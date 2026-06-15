from __future__ import annotations

import multiprocessing as mp
from pathlib import Path

from .worker_process_support import drain_events, spawn_queue_or_skip
from orchestrator.models import UiState
from orchestrator.worker import run_worker_process, terminate_process_tree


def test_worker_process_runs_empty_queue_to_completion(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    artifact_dir = tmp_path / "artifacts"
    corpus_dir = tmp_path / "corpus"
    for path in (input_dir, artifact_dir, corpus_dir):
        path.mkdir(parents=True, exist_ok=True)

    ui_state = UiState(
        input_folder=str(input_dir),
        artifact_folder=str(artifact_dir),
        corpus_output_folder=str(corpus_dir),
    )
    project_root = Path(__file__).resolve().parents[2]
    ctx = mp.get_context("spawn")
    worker_queue = spawn_queue_or_skip(ctx)
    cancel_event = ctx.Event()
    process = ctx.Process(
        target=run_worker_process,
        args=(str(project_root), "run", ui_state.to_dict(), worker_queue, cancel_event),
    )

    try:
        process.start()
        process.join(timeout=15)
        if process.is_alive():
            terminate_process_tree(process.pid)
            process.join(timeout=5)
            raise AssertionError("Worker-Prozess wurde nicht beendet")
        events = drain_events(worker_queue)
    finally:
        worker_queue.close()
        worker_queue.join_thread()

    assert process.exitcode == 0
    assert "snapshot" in events
    assert "done" in events
