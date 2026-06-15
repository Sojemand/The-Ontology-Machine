"""Shared helpers for input_catalog tests."""
from __future__ import annotations

from ingestion_layer_vision.models import atomic_json_write


def write_completed_raw(output_root, filename: str, content_hash: str, *, ingest_id: str = "11111111-1111-1111-1111-111111111111") -> None:
    raw_dir = output_root / "raw_extracts"
    raw_dir.mkdir(parents=True, exist_ok=True)
    atomic_json_write(
        raw_dir / f"{filename}.raw.json",
        {"schema_version": "optimizer_raw_v2", "source": {"content_hash": content_hash, "ingest_id": ingest_id}},
    )

