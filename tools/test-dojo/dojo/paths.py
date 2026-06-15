from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DojoPaths:
    dojo_root: Path
    tools_root: Path
    pipeline_root: Path
    config_path: Path
    suite_dir: Path
    report_root: Path
    run_root: Path


def resolve_paths() -> DojoPaths:
    dojo_root = Path(__file__).resolve().parents[1]
    tools_root = dojo_root.parent
    pipeline_root = tools_root.parent
    config_path = dojo_root / "dojo.config.json"
    config = _read_config(config_path)
    suite_dir = (dojo_root / str(config.get("suite_dir", "suites"))).resolve()
    report_root = (dojo_root / str(config.get("report_root", "../../.tmp/test-dojo/reports"))).resolve()
    run_root = (dojo_root / str(config.get("run_root", "../../.tmp/test-dojo/runs"))).resolve()
    return DojoPaths(
        dojo_root=dojo_root,
        tools_root=tools_root,
        pipeline_root=pipeline_root,
        config_path=config_path,
        suite_dir=suite_dir,
        report_root=report_root,
        run_root=run_root,
    )


def _read_config(path: Path) -> dict:
    import json

    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))
