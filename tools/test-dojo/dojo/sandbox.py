from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class DojoSandbox:
    run_id: str
    run_dir: Path
    report_dir: Path
    input_dir: Path
    output_dir: Path
    state_dir: Path
    artifact_dir: Path
    log_dir: Path
    screenshot_dir: Path
    trace_dir: Path

    def as_env(self) -> dict[str, str]:
        return {
            "VISION_PIPELINE_TEST_DOJO": "1",
            "VISION_PIPELINE_TEST_DOJO_RUN_ID": self.run_id,
            "VISION_PIPELINE_TEST_DOJO_RUN_DIR": str(self.run_dir),
            "VISION_PIPELINE_TEST_DOJO_REPORT_DIR": str(self.report_dir),
        }


def make_run_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def create_sandbox(run_root: Path, report_root: Path, run_id: str | None = None) -> DojoSandbox:
    actual_run_id = run_id or make_run_id()
    run_dir = run_root / actual_run_id
    report_dir = report_root / actual_run_id
    sandbox = DojoSandbox(
        run_id=actual_run_id,
        run_dir=run_dir,
        report_dir=report_dir,
        input_dir=run_dir / "input",
        output_dir=run_dir / "output",
        state_dir=run_dir / "state",
        artifact_dir=run_dir / "artifacts",
        log_dir=run_dir / "logs",
        screenshot_dir=report_dir / "screenshots",
        trace_dir=report_dir / "traces",
    )
    for path in (
        sandbox.run_dir,
        sandbox.report_dir,
        sandbox.input_dir,
        sandbox.output_dir,
        sandbox.state_dir,
        sandbox.artifact_dir,
        sandbox.log_dir,
        sandbox.screenshot_dir,
        sandbox.trace_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)
    return sandbox


def merged_env(base: dict[str, str] | None, sandbox: DojoSandbox) -> dict[str, str]:
    env = dict(base or os.environ)
    env.update(sandbox.as_env())
    return env
