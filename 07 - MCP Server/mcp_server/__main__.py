"""CLI entrypoint for the local Vision Pipeline MCP server."""

from __future__ import annotations

from .server import main


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
