"""Stable subprocess surface for Outlook store extraction."""
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
RUNTIME_VENDOR_DIR = PLUGIN_DIR / "runtime" / "vendor"
RUNTIME_PYTHON = PLUGIN_DIR / "runtime" / "python" / ("python.exe" if sys.platform == "win32" else "python")
_REEXEC_SENTINEL = "MAIL_OUTLOOK_STORE_RUNTIME_REEXEC"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ingestion_layer_file.mail_runtime import (
    build_preview_blocks,
    extract_outlook_store_bundle,
    selftest_outlook_store_backend,
    summarize_manifest,
)


def extract(input_path: str, config: dict) -> dict:
    _prepend_vendor_paths(config)
    start = time.perf_counter_ns()
    try:
        bundle_root, manifest = extract_outlook_store_bundle(input_path, config)
        metadata = summarize_manifest(manifest)
        metadata["mail_bundle_path"] = str((bundle_root / "manifest.json").resolve())
        metadata["outlook_store_backend"] = str(manifest.get("backend") or "")
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
    _prepend_vendor_paths({})
    ok, detail = selftest_outlook_store_backend()
    if ok:
        return {"status": "ok", "version": "1.0.0", "detail": detail}
    remediation = (
        f"Lege ein pypff/libpff-Paket unter {RUNTIME_VENDOR_DIR} ab "
        "oder stelle einen funktionierenden Outlook-COM-Fallback bereit."
    )
    return {"status": "error", "version": "1.0.0", "error": f"{detail}; {remediation}"}


def _prepend_vendor_paths(config: dict) -> None:
    configured_vendor = str(config.get("vendor_path", "") or "").strip()
    candidate_paths = [RUNTIME_VENDOR_DIR]
    if configured_vendor:
        configured_path = Path(configured_vendor)
        if not configured_path.is_absolute():
            configured_path = (PLUGIN_DIR / configured_path).resolve()
        candidate_paths.insert(0, configured_path)
    for candidate in candidate_paths:
        if candidate.exists() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))


def _should_reexec_with_runtime() -> bool:
    if str(Path(sys.executable).resolve()) == str(RUNTIME_PYTHON.resolve()):
        return False
    if not RUNTIME_PYTHON.exists():
        return False
    if not any(RUNTIME_VENDOR_DIR.glob("pypff*.pyd")):
        return False
    if sys.version_info[:2] == (3, 9):
        return False
    return os.environ.get(_REEXEC_SENTINEL, "") != "1"


def _reexec_with_runtime(argv: list[str]) -> int:
    env = dict(os.environ)
    env[_REEXEC_SENTINEL] = "1"
    result = subprocess.run(
        [str(RUNTIME_PYTHON), str(Path(__file__).resolve()), *argv],
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
