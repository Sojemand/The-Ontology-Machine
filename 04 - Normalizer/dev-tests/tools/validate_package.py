from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_package_env import validate_environment
from validate_package_policy import (
    DEV_SPEC,
    PROJECT_ROOT,
    RUNTIME_SPEC,
    SKIP_DIR_NAMES,
    VENDOR_PYTHON_ZIP,
    parse_lockfile,
    parse_wheelhouse,
    scan_text_files,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the portable offline packaging for Normalizer Vision.")
    parser.add_argument("--runtime-only", action="store_true", help="Validate only the bundled runtime.")
    parser.add_argument("--dev-only", action="store_true", help="Validate only the development environment.")
    args = parser.parse_args(argv)

    issues: list[str] = []
    if not VENDOR_PYTHON_ZIP.exists():
        issues.append(f"Portable Python-Basis fehlt: {VENDOR_PYTHON_ZIP}")
    if args.runtime_only and args.dev_only:
        issues.append("--runtime-only und --dev-only schliessen sich aus")

    specs = _selected_specs(runtime_only=args.runtime_only, dev_only=args.dev_only)
    issues.extend(scan_text_files(PROJECT_ROOT, skip_dir_names=SKIP_DIR_NAMES | {"dev-tests"}))
    for spec in specs:
        issues.extend(validate_environment(spec))

    if issues:
        for issue in issues:
            print(f"[FAIL] {issue}")
        return 1
    print("[OK] Portable package validation passed.")
    return 0


def _selected_specs(*, runtime_only: bool, dev_only: bool):
    if runtime_only:
        return [RUNTIME_SPEC]
    if dev_only:
        return [DEV_SPEC]
    return [RUNTIME_SPEC, DEV_SPEC]


if __name__ == "__main__":
    raise SystemExit(main())
