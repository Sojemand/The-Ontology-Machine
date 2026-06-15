"""Small healthcheck contract for the MCP Server module slot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..atomic_io import atomic_json_write
from ..healthcheck import run_healthcheck


def _healthcheck(*, strict_runtime: bool = False) -> dict:
    return run_healthcheck(strict_runtime=strict_runtime)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request")
    parser.add_argument("--response")
    parser.add_argument("--healthcheck", action="store_true")
    args = parser.parse_args(argv)
    response = _healthcheck(strict_runtime=args.healthcheck)
    if args.healthcheck:
        print(json.dumps(response, ensure_ascii=False))
        return 0 if response["healthy"] else 1
    if args.response:
        atomic_json_write(Path(args.response), response)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
