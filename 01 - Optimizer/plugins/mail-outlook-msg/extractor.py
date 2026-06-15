"""Stable subprocess surface for Outlook .msg / .oft extraction."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

PLUGIN_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PLUGIN_DIR.parents[1]
MODULE_RUNTIME_PYTHON = PROJECT_ROOT / "runtime" / "python" / ("python.exe" if sys.platform == "win32" else "python")
_REEXEC_SENTINEL = "MAIL_OUTLOOK_MSG_RUNTIME_REEXEC"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ingestion_layer_file.mail_runtime import build_preview_blocks, extract_msg_bundle, summarize_manifest


def _should_reexec_with_runtime() -> bool:
    if not MODULE_RUNTIME_PYTHON.exists():
        return False
    if os.environ.get(_REEXEC_SENTINEL, "") == "1":
        return False
    try:
        return Path(sys.executable).resolve() != MODULE_RUNTIME_PYTHON.resolve()
    except OSError:
        return True


def _reexec_with_runtime(argv: list[str]) -> int:
    env = dict(os.environ)
    env[_REEXEC_SENTINEL] = "1"
    result = subprocess.run(
        [str(MODULE_RUNTIME_PYTHON), str(Path(__file__).resolve()), *argv],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)
    return int(result.returncode)


def extract(input_path: str, config: dict) -> dict:
    del config
    start = time.perf_counter_ns()
    try:
        bundle_root, manifest = extract_msg_bundle(input_path)
        metadata = summarize_manifest(manifest)
        metadata["mail_bundle_path"] = str((bundle_root / "manifest.json").resolve())
        return {
            "status": "success",
            "blocks": build_preview_blocks(manifest),
            "metadata": metadata,
            "errors": [],
            "processing_time_ms": (time.perf_counter_ns() - start) // 1_000_000,
        }
    except Exception as exc:
        return {
            "status": "error",
            "blocks": [],
            "metadata": {},
            "errors": [str(exc)],
            "processing_time_ms": (time.perf_counter_ns() - start) // 1_000_000,
        }
        

def selftest() -> dict:
    try:
        import extract_msg  # noqa: F401

        return {"status": "ok", "version": "1.0.0"}
    except Exception as exc:
        return {"status": "error", "version": "1.0.0", "error": str(exc)}


def main() -> int:
    if _should_reexec_with_runtime():
        return _reexec_with_runtime(sys.argv[1:])
    parser = argparse.ArgumentParser()
    parser.add_argument("--extract", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--input", default="")
    parser.add_argument("--config", default="{}")
    args = parser.parse_args()
    if args.selftest:
        payload = selftest()
    elif args.extract:
        payload = extract(args.input, json.loads(args.config))
    else:
        payload = {
            "status": "error",
            "blocks": [],
            "metadata": {},
            "errors": ["Kein Modus gewaehlt"],
            "processing_time_ms": 0,
        }
    json.dump(payload, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
