from __future__ import annotations

from pathlib import Path


PIPELINE_ROOT = Path(__file__).resolve().parents[3]
DOC_CASES = (
    (
        PIPELINE_ROOT / "01 - Optimizer" / "README.md",
        ("optimizer_raw_v2", "optimizer_profile", "runtime_policy_path", "runtime_semantic_assets_v1"),
    ),
    (
        PIPELINE_ROOT / "01 - Optimizer" / "EDIT_CONTRACT.md",
        ("optimizer.debug_capabilities", "runtime_policy_path", "runtime_semantic_assets_v1", "raw-first"),
    ),
    (
        PIPELINE_ROOT / "04 - Normalizer" / "README.md",
        (
            "SPEC_Projection_Release.md",
            "taxonomy_sources",
            "routing.surface_signals",
            "semantic_extraction_policy_v2",
            "projection_routing",
            "projection_hint_mode=advisory",
            "projection.selection.reason",
        ),
    ),
    (
        PIPELINE_ROOT / "04 - Normalizer" / "EDIT_CONTRACT.md",
        ("projection_routing", "routing.surface_signals", "semantic_release_authoring", "taxonomy_sources"),
    ),
)


def test_projection_release_docs_stay_under_200_lines() -> None:
    for path, _tokens in DOC_CASES:
        assert len(path.read_text(encoding="utf-8").splitlines()) <= 200, path


def test_projection_release_docs_keep_step4_terminology() -> None:
    for path, tokens in DOC_CASES:
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            assert token in text, f"{token} missing in {path}"
