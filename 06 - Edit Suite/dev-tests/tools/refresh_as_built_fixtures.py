from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
import sys

MODULE_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = MODULE_ROOT.parent
FIXTURE_ROOT = MODULE_ROOT / "dev-tests" / "fixtures" / "as_built"

sys.path.insert(0, str(MODULE_ROOT))

from edit_suite.contract_runtime import invoke_owner_contract


CASES = (
    {
        "slot_name": "01 - Optimizer",
        "env_name": "OPTIMIZER_HOME",
        "contract_rel": "ingestion_layer_vision/edit_contract",
        "surface_fixture": "optimizer_describe_surfaces.json",
        "summary_fixture": "optimizer_summary.txt",
    },
)


def main() -> int:
    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="edit-suite-as-built-") as temp_dir:
        temp_root = Path(temp_dir)
        for case in CASES:
            payload = _describe_contract(case, temp_root=temp_root)
            _write_json(FIXTURE_ROOT / case["surface_fixture"], payload["surfaces"])
            (FIXTURE_ROOT / case["summary_fixture"]).write_text(payload["module_summary"] + "\n", encoding="utf-8")
            print(f"updated {case['surface_fixture']}")
            print(f"updated {case['summary_fixture']}")
    return 0


def _describe_contract(case: dict[str, str], *, temp_root: Path) -> dict:
    module_root = PIPELINE_ROOT / case["slot_name"]
    home_root = temp_root / (module_root.name.replace(" ", "_").replace("-", "_") + "_home")
    os.environ[case["env_name"]] = str(home_root)
    return invoke_owner_contract(
        module_root=module_root,
        contract_path=str((module_root / case["contract_rel"]).resolve()),
        state_root=temp_root / "suite_state",
        payload={"action": "describe_surfaces"},
    )


def _write_json(path: Path, payload: object) -> None:
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())

