from __future__ import annotations

import json
from pathlib import Path

TEST_DATA = Path(__file__).parent / "test_data"


def write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def file_structured(*, content_hash: str) -> dict:
    return {
        "processing": {
            "interpreter_profile": "file",
            "model_confidence": 0.9,
            "needs_review": False,
            "review_reason": None,
            "vision_used": True,
        },
        "content": {
            "free_text": "TA-1\nLeipzig\nPGA 800 in Transportkiste\nAX 2460 in Transportkiste",
            "fields": {"document_id": "TA-1", "destination": "Leipzig"},
            "rows": [
                {"description": "PGA 800 in Transportkiste", "menge": "1", "bezeichnung": "PGA 800 in Transportkiste"},
                {"description": "AX 2460 in Transportkiste", "menge": "2", "bezeichnung": "AX 2460 in Transportkiste"},
            ],
        },
        "source": {"file_name": "transport.docx", "content_hash": content_hash},
    }


def file_raw(*, content_hash: str) -> dict:
    return {
        "doc": {"file_name": "transport.docx", "content_hash": content_hash},
        "pages": [
            {
                "page": 1,
                "tables": [
                    {
                        "rows": [
                            ["1", "PGA 800 in Transportkiste", "PGA 800 in Transportkiste"],
                            ["2", "AX 2460 in Transportkiste", "AX 2460 in Transportkiste"],
                        ]
                    }
                ],
                "blocks": [{"role": "paragraph", "text": "Dokument TA-1\nZiel Leipzig"}],
            }
        ],
    }


def report_path(root: Path, name: str) -> Path:
    return root / "reports" / name


def debug_payload(session_root: Path, *, mode: str, **payload: object) -> dict[str, object]:
    body: dict[str, object] = {
        "action": "debug_run",
        "mode": mode,
        "session_root": str(session_root),
        "output_root": str(session_root / "outputs"),
        "options": {
            "raw_evidence": {},
            "check_toggles": {
                "free_text": True,
                "context_scalars": True,
                "content_fields": True,
                "rows": True,
            },
        },
    }
    body.update(payload)
    return body
