from __future__ import annotations

import json
import sys
from pathlib import Path


PIPELINE_ROOT = Path(__file__).resolve().parents[3]
NORMALIZER_ROOT = PIPELINE_ROOT / "04 - Normalizer"
README_PATH = NORMALIZER_ROOT / "README.md"
EDIT_CONTRACT_PATH = NORMALIZER_ROOT / "EDIT_CONTRACT.md"
MANIFEST_PATH = NORMALIZER_ROOT / "module-manifest.json"
TOKENS = (
    "taxonomy_sources",
    "routing.surface_signals",
    "semantic_release_authoring",
    "projection_hint",
    "projection.selection.reason",
)


def test_normalizer_docs_and_slot_summary_keep_step11_terminology() -> None:
    if str(NORMALIZER_ROOT) not in sys.path:
        sys.path.insert(0, str(NORMALIZER_ROOT))
    from normalizer_vision.edit_contract.summary import build_module_summary

    texts = {
        "README": README_PATH.read_text(encoding="utf-8"),
        "EDIT_CONTRACT": EDIT_CONTRACT_PATH.read_text(encoding="utf-8"),
        "Slot Summary": build_module_summary(),
    }
    for label, text in texts.items():
        for token in TOKENS:
            assert token in text, f"{token} missing in {label}"


def test_normalizer_manifest_keeps_public_semantic_actions() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert {
        "normalize_document",
        "build_projection_catalog",
        "build_runtime_semantic_assets",
        "publish_semantic_release",
    }.issubset(set(manifest["actions"]))
