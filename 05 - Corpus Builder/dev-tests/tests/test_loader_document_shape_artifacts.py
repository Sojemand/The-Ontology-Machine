from __future__ import annotations

import json

from tests.fixtures.loader_io import load_input_file

def test_original_artifact_blob_is_opt_in_and_bounded(
    db,
    vision_structured,
    vision_normalized,
    vision_validation_report,
    make_input_pair,
    tmp_path,
):
    source_file = tmp_path / "source.pdf"
    source_file.write_bytes(b"source bytes")

    structured = json.loads(json.dumps(vision_structured))
    normalized = json.loads(json.dumps(vision_normalized))
    for payload in (structured, normalized):
        payload["source"] = dict(payload.get("source") or {})
        payload["source"]["file_name"] = source_file.name
        payload["source"]["file_path"] = str(source_file)
        payload["source"]["content_hash"] = f"sha256:{payload['source'].get('content_hash', 'artifact')}-default"

    json_path = make_input_pair(
        "artifact_blob_default",
        structured,
        vision_report=vision_validation_report,
        normalized=normalized,
    )
    assert load_input_file(db, json_path).status == "loaded"
    row = db.execute(
        "SELECT original_file_name, original_media_type, length(original_blob) AS blob_size "
        "FROM document_payloads WHERE document_id = ?",
        ("artifact_blob_default",),
    ).fetchone()
    assert row["original_file_name"] == "source.pdf"
    assert row["original_media_type"] == "application/pdf"
    assert row["blob_size"] is None

    for payload in (structured, normalized):
        payload["source"]["content_hash"] = "sha256:artifact-opt-in"
    opt_in_path = make_input_pair(
        "artifact_blob_opt_in",
        structured,
        vision_report=vision_validation_report,
        normalized=normalized,
    )
    assert load_input_file(
        db,
        opt_in_path,
        persist_original_artifact_in_db=True,
        max_original_artifact_bytes=20,
    ).status in {"loaded", "archived_and_loaded"}
    assert db.execute(
        "SELECT length(original_blob) FROM document_payloads WHERE document_id = ?",
        ("artifact_blob_opt_in",),
    ).fetchone()[0] == len(b"source bytes")

    for payload in (structured, normalized):
        payload["source"]["content_hash"] = "sha256:artifact-too-large"
    too_large_path = make_input_pair(
        "artifact_blob_too_large",
        structured,
        vision_report=vision_validation_report,
        normalized=normalized,
    )
    assert load_input_file(
        db,
        too_large_path,
        persist_original_artifact_in_db=True,
        max_original_artifact_bytes=4,
    ).status in {"loaded", "archived_and_loaded"}
    assert db.execute(
        "SELECT length(original_blob) FROM document_payloads WHERE document_id = ?",
        ("artifact_blob_too_large",),
    ).fetchone()[0] is None
