"""Stable subprocess surface for RFC822 mail extraction."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

PLUGIN_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PLUGIN_DIR.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ingestion_layer_file.mail_runtime import build_preview_blocks, extract_rfc822_bundle, summarize_manifest


def extract(input_path: str, config: dict) -> dict:
    del config
    start = time.perf_counter_ns()
    try:
        bundle_root, manifest = extract_rfc822_bundle(input_path)
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
        import email  # noqa: F401
        import mailbox  # noqa: F401

        return {"status": "ok", "version": "1.0.0"}
    except Exception as exc:
        return {"status": "error", "version": "1.0.0", "error": str(exc)}


def main() -> int:
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
