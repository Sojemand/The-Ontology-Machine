"""Small JSON-RPC/MCP protocol surface for local stdio transport."""

from __future__ import annotations

import json
from typing import Any, BinaryIO

from . import __version__
from .tools import ToolFailure, call_tool, result_as_text, visible_tool_definitions

JSONRPC = "2.0"
DEFAULT_PROTOCOL_VERSION = "2024-11-05"


def handle_message(message: dict[str, Any]) -> dict[str, Any] | None:
    method = str(message.get("method") or "")
    request_id = message.get("id")
    try:
        if method == "initialize":
            return _response(request_id, _initialize_result(message))
        if method == "notifications/initialized":
            return None
        if method == "ping":
            return _response(request_id, {})
        if method == "tools/list":
            return _response(request_id, {"tools": visible_tool_definitions()})
        if method == "tools/call":
            return _response(request_id, _call_tool_result(message))
        if request_id is None:
            return None
        return _error(request_id, -32601, f"Unbekannte Methode: {method}")
    except ToolFailure as exc:
        return _response(request_id, {"content": [{"type": "text", "text": str(exc)}], "isError": True})
    except Exception as exc:  # pragma: no cover - defensive protocol boundary
        return _error(request_id, -32603, str(exc))


def encode_message(message: dict[str, Any]) -> str:
    return json.dumps(message, ensure_ascii=False, separators=(",", ":"))


def decode_message(raw: str | bytes) -> dict[str, Any]:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8-sig")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("JSON-RPC Message muss ein Objekt sein.")
    return payload


def encode_framed_message(message: dict[str, Any]) -> bytes:
    body = encode_message(message).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    return header + body


def read_framed_message(stream: BinaryIO) -> dict[str, Any] | None:
    first = _read_non_empty_line(stream)
    if first is None:
        return None
    if first.lstrip().startswith(b"{"):
        return decode_message(first)

    headers = [first]
    while True:
        line = stream.readline()
        if line == b"":
            raise ValueError("Unerwartetes EOF im MCP-Header.")
        if line in (b"\r\n", b"\n"):
            break
        headers.append(line)

    length = _content_length(headers)
    body = stream.read(length)
    if len(body) != length:
        raise ValueError("Unerwartetes EOF im MCP-Body.")
    return decode_message(body)


def _read_non_empty_line(stream: BinaryIO) -> bytes | None:
    while True:
        line = stream.readline()
        if line == b"":
            return None
        if line.strip():
            return line


def _content_length(headers: list[bytes]) -> int:
    for raw_header in headers:
        try:
            header = raw_header.decode("ascii").strip()
        except UnicodeDecodeError:
            continue
        name, sep, value = header.partition(":")
        if sep and name.lower() == "content-length":
            try:
                length = int(value.strip())
            except ValueError:
                break
            if length > 0:
                return length
    raise ValueError("MCP-Header ohne gueltiges Content-Length.")


def _initialize_result(message: dict[str, Any]) -> dict[str, Any]:
    params = message.get("params") if isinstance(message.get("params"), dict) else {}
    protocol_version = str(params.get("protocolVersion") or DEFAULT_PROTOCOL_VERSION)
    return {
        "protocolVersion": protocol_version,
        "capabilities": {"tools": {"listChanged": False}},
        "serverInfo": {"name": "vision-pipeline-mcp-server", "version": __version__},
    }


def _call_tool_result(message: dict[str, Any]) -> dict[str, Any]:
    params = message.get("params")
    if not isinstance(params, dict):
        raise ToolFailure("tools/call erwartet params.")
    name = str(params.get("name") or "").strip()
    arguments = params.get("arguments")
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        raise ToolFailure("tools/call arguments muss ein Objekt sein.")
    result = call_tool(name, arguments)
    return {"content": [{"type": "text", "text": result_as_text(result)}], "structuredContent": result}


def _response(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": JSONRPC, "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": JSONRPC, "id": request_id, "error": {"code": code, "message": message}}
