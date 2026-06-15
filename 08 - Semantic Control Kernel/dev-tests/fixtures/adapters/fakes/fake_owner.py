from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--response", required=True)
    args = parser.parse_args(argv)

    request_path = Path(args.request)
    response_path = Path(args.response)
    request = json.loads(request_path.read_text(encoding="utf-8"))
    payload = request.get("request_payload", {})
    if not isinstance(payload, dict):
        payload = {}
    mode = payload.get("mode", "success")

    print(f"fake-owner mode={mode}")
    print(f"adapter={os.environ.get('VISION_KERNEL_ADAPTER_CALL_ID', '')}")

    if mode == "timeout":
        time.sleep(float(payload.get("sleep_seconds", 10)))
        return 0
    if mode == "spawn_child_timeout":
        marker_path = Path(str(payload["child_marker_path"]))
        child_code = (
            "import pathlib,time;"
            f"time.sleep({float(payload.get('child_sleep_seconds', 0.8))!r});"
            f"pathlib.Path({str(marker_path)!r}).write_text('late child write', encoding='utf-8')"
        )
        subprocess.Popen([sys.executable, "-c", child_code])
        time.sleep(float(payload.get("sleep_seconds", 10)))
        return 0
    if mode == "delayed_success":
        time.sleep(float(payload.get("sleep_seconds", 0.2)))
        _write_response(response_path, _success_payload(request, payload))
        return 0
    if mode == "missing_response":
        return 0
    if mode == "invalid_json":
        response_path.write_text("{invalid json", encoding="utf-8")
        return 0
    if mode == "error":
        _write_response(
            response_path,
            {
                "schema_version": "fake_owner_response.v1",
                "status": "error",
                "owner_module": "fake_corpus_builder",
                "owner_action": request.get("owner_action"),
                "message": "owner failed",
                "error": {"code": "fake_owner_error"},
                "diagnostics": [{"code": "fake_owner_error"}],
            },
        )
        return 2
    if mode == "missing_capability":
        _write_response(
            response_path,
            {
                "schema_version": "fake_owner_response.v1",
                "status": "missing_capability",
                "owner_module": "fake_corpus_builder",
                "owner_action": request.get("owner_action"),
                "message": "capability missing",
                "detail": {},
                "target_identity_proof": {},
                "diagnostics": [{"code": "fake_missing_capability"}],
            },
        )
        return 0

    _write_response(response_path, _success_payload(request, payload))
    return 0


def _success_payload(request: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    proof = payload.get("target_identity_proof")
    if not isinstance(proof, dict):
        proof = {
            "artifact_root_path_hash": "artifact_hash_123",
            "database_path_hash": "database_hash_123",
            "release_fingerprint": "release_fingerprint_123",
        }
    return {
        "schema_version": "fake_owner_response.v1",
        "status": "ok",
        "owner_module": "fake_corpus_builder",
        "owner_action": request.get("owner_action"),
        "message": "created",
        "detail": {"created": True, "request_payload_echo": payload},
        "target_identity_proof": proof,
        "diagnostics": [{"code": "fake_owner_success"}],
    }


def _write_response(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
