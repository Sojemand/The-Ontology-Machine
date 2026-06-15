"""Local stdio server loop for the Vision Pipeline MCP module."""

from __future__ import annotations

import argparse
import sys

from .protocol import encode_framed_message, handle_message, read_framed_message
from .tools import visible_tool_definitions


def serve_stdio() -> int:
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    while True:
        try:
            message = read_framed_message(stdin)
        except Exception as exc:  # pragma: no cover - malformed transport input
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": str(exc)},
            }
        else:
            if message is None:
                return 0
            response = handle_message(message)
        if response is None:
            continue
        stdout.write(encode_framed_message(response))
        stdout.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Vision Pipeline local MCP delegate server.")
    parser.add_argument("--list-tools", action="store_true", help="Print the MCP tool catalog as JSON and exit.")
    args = parser.parse_args(argv)
    if args.list_tools:
        import json

        print(json.dumps({"tools": visible_tool_definitions()}, ensure_ascii=False, indent=2))
        return 0
    return serve_stdio()
