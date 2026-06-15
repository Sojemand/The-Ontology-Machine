from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PIPELINE_ROOT = Path(__file__).resolve().parents[3]
NORMALIZER_ROOT = PIPELINE_ROOT / "04 - Normalizer"
TOOLS_ROOT = PIPELINE_ROOT / "tools"
FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "runtime_semantic_assets_v1.json"

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from refresh_phase0_artifacts import build_phase0_artifacts, project_optimizer_runtime_payload, refresh_phase0_artifacts


def build_runtime_semantic_fixture() -> dict[str, object]:
    _, runtime_payload = build_phase0_artifacts(NORMALIZER_ROOT)
    return project_optimizer_runtime_payload(runtime_payload, reference_fixture_path=FIXTURE_PATH)


def write_fixture(path: Path = FIXTURE_PATH) -> Path:
    payload = build_runtime_semantic_fixture()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Refresh the checked-in Optimizer runtime semantic assets fixture from the real 04 compiler."
    )
    parser.add_argument("--output", type=Path, default=FIXTURE_PATH, help="Target JSON path. Defaults to the checked-in fixture.")
    args = parser.parse_args(argv)
    if args.output == FIXTURE_PATH:
        result = refresh_phase0_artifacts()
        print(json.dumps(result, ensure_ascii=False))
        return 0
    written = write_fixture(args.output)
    print(f"updated {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

