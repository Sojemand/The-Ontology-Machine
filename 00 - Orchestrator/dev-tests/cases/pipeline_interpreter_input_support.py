from __future__ import annotations

import json
from pathlib import Path


def _write_raw(
    raw_path: Path,
    *,
    source: dict[str, object],
    context: dict[str, object],
    blocks: list[dict[str, object]],
    optimizer_profile: str = "vision",
) -> None:
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(
        json.dumps(
            {
                "schema_version": "optimizer_raw_v2",
                "optimizer_profile": optimizer_profile,
                "source": source,
                "extraction": {"plugin_name": "fake", "plugin_version": "1.0.0", "processing_time_ms": 1},
                "metadata": {},
                "context": context,
                "ocr_reference": {"blocks": blocks},
            }
        ),
        encoding="utf-8",
    )
