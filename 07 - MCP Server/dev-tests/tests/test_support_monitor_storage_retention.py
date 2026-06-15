from __future__ import annotations

from pathlib import Path

from mcp_server import support_monitor_storage


def test_support_jsonl_retention_keeps_latest_records(tmp_path: Path) -> None:
    path = tmp_path / "support_events.jsonl"
    for index in range(5):
        support_monitor_storage.append_jsonl(path, {"index": index}, max_records=3, max_bytes=0)

    assert [item["index"] for item in support_monitor_storage.load_jsonl(path)] == [2, 3, 4]


def test_support_jsonl_retention_bounds_file_size(tmp_path: Path) -> None:
    path = tmp_path / "support_events.jsonl"
    for index in range(4):
        support_monitor_storage.append_jsonl(
            path,
            {"index": index, "message": "x" * 50},
            max_records=10,
            max_bytes=160,
        )

    items = support_monitor_storage.load_jsonl(path)
    assert items[-1]["index"] == 3
    assert len(items) < 4
    assert len(path.read_bytes()) <= 160
