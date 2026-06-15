from __future__ import annotations

import argparse
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from build_runtime_env import DEV_TARGET, RUNTIME_TARGET, build_target, runtime_manifest_payload, write_python_path_file, write_runtime_manifest

_runtime_manifest_payload = runtime_manifest_payload
_write_python_path_file = write_python_path_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build portable offline Python environments for Normalizer Vision.")
    parser.add_argument("--runtime", action="store_true", help="Build the bundled runtime/python environment.")
    parser.add_argument("--dev", action="store_true", help="Build the local dev-tests/.venv development environment.")
    parser.add_argument("--no-clean", action="store_true", help="Reuse existing target directories when possible.")
    parser.add_argument(
        "--write-runtime-manifest",
        action="store_true",
        help="Prune GUI-only runtime artefacts and rewrite runtime/runtime-manifest.json.",
    )
    args = parser.parse_args(argv)

    if args.write_runtime_manifest:
        write_runtime_manifest()
        return 0

    targets = [RUNTIME_TARGET, DEV_TARGET] if not args.runtime and not args.dev else []
    if args.runtime:
        targets.append(RUNTIME_TARGET)
    if args.dev:
        targets.append(DEV_TARGET)
    for target in targets:
        print(f"[BUILD] {target.name} -> {target.target_dir}")
        build_target(target, clean=not args.no_clean)
    write_runtime_manifest()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
