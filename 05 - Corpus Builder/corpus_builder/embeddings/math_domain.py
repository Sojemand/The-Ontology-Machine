"""Vector math and JSON parsing helpers for embeddings."""

from __future__ import annotations

import json
import math
from typing import Any

try:
    import numpy as np
except ImportError:  # pragma: no cover - optional fast path
    np = None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if np is not None:
        vector_a = np.array(a, dtype=np.float32)
        vector_b = np.array(b, dtype=np.float32)
        norm_a = np.linalg.norm(vector_a)
        norm_b = np.linalg.norm(vector_b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(vector_a, vector_b) / (norm_a * norm_b))
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def parse_document_json(raw_json: str) -> tuple[dict[str, Any] | None, str | None]:
    if not raw_json:
        return None, "empty"
    try:
        document = json.loads(raw_json)
    except Exception:
        return None, "invalid_json"
    if not isinstance(document, dict):
        return None, "not_object"
    return document, None
