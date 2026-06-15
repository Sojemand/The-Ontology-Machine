"""Stable surface for the docx-python Word extractor."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PLUGIN_DIR = Path(__file__).resolve().parent
MODULE_ROOT = PLUGIN_DIR.parent.parent
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from docx_extractor import extract, selftest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extract", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--input", default="")
    parser.add_argument("--config", default="{}")
    args = parser.parse_args()

    if args.selftest:
        result = selftest()
    elif args.extract:
        result = extract(args.input, json.loads(args.config))
    else:
        result = {
            "status": "error",
            "blocks": [],
            "metadata": {},
            "errors": ["Kein Modus gewaehlt"],
            "processing_time_ms": 0,
        }

    json.dump(result, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
