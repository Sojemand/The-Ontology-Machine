from __future__ import annotations

import subprocess
from pathlib import Path

PIPELINE_ARTIFACT_DIRS = (
    Path("Input"),
    Path("Corpus"),
    Path("Documents"),
    Path("Documents") / "logs",
    Path("Documents") / "normalized",
    Path("Documents") / "originals",
    Path("Documents") / "page_images",
    Path("Documents") / "raw_extracts",
    Path("Documents") / "requests",
    Path("Documents") / "structured",
    Path("Documents") / "validation",
    Path("Error Cases"),
)
DEFAULT_PIPELINE_RUN_TIMEOUT_SECONDS = 3600
PIPELINE_RUN_TIMEOUT_LIMIT_SECONDS = 24 * 60 * 60
PIPELINE_INPUT_PREVIEW_LIMIT = 200
PIPELINE_RUN_LOG_TAIL_LINES = 80
WORKSPACE_NORMALIZER_AUTHORING_DIR = Path(".vp") / "n"
_PIPELINE_RUN_PROCESSES: dict[str, subprocess.Popen] = {}
_REAL_POPEN_TYPE = subprocess.Popen

__all__ = [name for name in globals() if not name.startswith("__")]
