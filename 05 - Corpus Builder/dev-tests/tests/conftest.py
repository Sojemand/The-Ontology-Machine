"""Thin shared test bootstrap for Corpus Builder Vision."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.fixtures.payload_fixtures import (
    files_validation_report,
    legacy_validation_report,
    mixed_structured,
    vision_normalized,
    vision_structured,
    vision_validation_report,
)
from tests.fixtures.runtime_fixtures import db, default_config, make_input_pair
