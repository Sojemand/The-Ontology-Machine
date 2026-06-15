from __future__ import annotations

import json
import sys
from pathlib import Path


PIPELINE_ROOT = Path(__file__).resolve().parents[3]
NORMALIZER_ROOT = PIPELINE_ROOT / "04 - Normalizer"
NORMALIZER_DEV_TESTS_ROOT = NORMALIZER_ROOT / "dev-tests"
TOOLS_ROOT = PIPELINE_ROOT / "tools"
OPTIMIZER_FIXTURE_PATH = PIPELINE_ROOT / "01 - Optimizer" / "dev-tests" / "fixtures" / "runtime_semantic_assets_v1.json"
CORPUS_RELEASE_PATH = PIPELINE_ROOT / "05 - Corpus Builder" / "config" / "semantic_release.default.json"
CORPUS_STAGE_RELEASE_PATH = PIPELINE_ROOT / "05 - Corpus Builder" / "dist" / "stage" / "config" / "semantic_release.default.json"
EXPECTED_DEFAULT_PROJECTION_IDS = [
    "business.customer.communication.default.v1",
    "community.spiritual.default.v1",
    "finance.default.v1",
    "health.care.default.v1",
    "housing.default.v1",
    "legal.public_admin.default.v1",
    "operations.default.v1",
    "people.identity.default.v1",
    "personal.expression.default.v1",
    "personal.wellbeing.default.v1",
    "technical.default.v1",
]

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))
if str(NORMALIZER_DEV_TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(NORMALIZER_DEV_TESTS_ROOT))

from refresh_phase0_artifacts import project_optimizer_runtime_payload
from tests.fixtures.taxonomy_refactor_baseline import normalize_phase0_release_payload, normalize_phase0_runtime_payload


def test_corpus_builder_default_release_identity_is_immutable() -> None:
    published = json.loads(CORPUS_RELEASE_PATH.read_text(encoding="utf-8"))

    assert published["release_id"] == "semantic_release.default"
    assert published["master_taxonomy_id"] == "normalizer_taxonomy.master"
    assert published["master_taxonomy_version"] == "2026-03-28.v6"
    assert published["projection_ids"] == EXPECTED_DEFAULT_PROJECTION_IDS

    projections = published.get("projections")
    assert isinstance(projections, list)
    assert [projection.get("projection_id") for projection in projections] == EXPECTED_DEFAULT_PROJECTION_IDS
    assert all(projection.get("projection_family") == "default" for projection in projections)
    assert all(str(projection.get("projection_id", "")).endswith(".default.v1") for projection in projections)


def test_corpus_builder_default_release_uses_current_optimizer_ocr_contract() -> None:
    published = json.loads(CORPUS_RELEASE_PATH.read_text(encoding="utf-8"))
    payload_text = json.dumps(published, sort_keys=True)
    ocr_defaults = published["runtime_semantic_assets"]["vision_policy_bundle"]["ocr_policy"]["defaults"]

    assert ocr_defaults["ocr_plugin"]["preferred_plugin"] == "optimizer-llm-ocr"
    assert "phase19" not in payload_text
    assert "ocr-paddleocr" not in payload_text
    assert "paddlevl" not in payload_text
    assert "device_policy" not in payload_text


def test_optimizer_runtime_fixture_matches_real_normalizer_compiler() -> None:
    if str(NORMALIZER_ROOT) not in sys.path:
        sys.path.insert(0, str(NORMALIZER_ROOT))
    from normalizer_vision.runtime_semantic_assets import build_runtime_semantic_assets
    from normalizer_vision.semantic_release import build_semantic_release

    actual = normalize_phase0_runtime_payload(
        project_optimizer_runtime_payload(
            build_runtime_semantic_assets(build_semantic_release(NORMALIZER_ROOT)).to_dict(),
            reference_fixture_path=OPTIMIZER_FIXTURE_PATH,
        )
    )
    expected = normalize_phase0_runtime_payload(json.loads(OPTIMIZER_FIXTURE_PATH.read_text(encoding="utf-8")))

    assert actual == expected


def test_corpus_builder_saved_release_matches_real_normalizer_compiler() -> None:
    if str(NORMALIZER_ROOT) not in sys.path:
        sys.path.insert(0, str(NORMALIZER_ROOT))
    from normalizer_vision.semantic_release import build_semantic_release

    expected = normalize_phase0_release_payload(build_semantic_release(NORMALIZER_ROOT))
    published = normalize_phase0_release_payload(json.loads(CORPUS_RELEASE_PATH.read_text(encoding="utf-8")))
    staged = normalize_phase0_release_payload(json.loads(CORPUS_STAGE_RELEASE_PATH.read_text(encoding="utf-8")))

    assert published == expected
    assert staged == published


def test_phase0_normalization_ignores_order_only_projection_drift() -> None:
    left_release = {
        "created_at": "2026-04-04T08:00:00Z",
        "fingerprint": "sha256:shared",
        "projection_ids": ["finance.default.v1", "housing.default.v1"],
        "projections": [
            {"projection_id": "housing.default.v1", "label": "Housing"},
            {"projection_id": "finance.default.v1", "label": "Finance"},
        ],
    }
    right_release = {
        "created_at": "2026-04-04T09:00:00Z",
        "fingerprint": "sha256:shared",
        "projection_ids": ["housing.default.v1", "finance.default.v1"],
        "projections": [
            {"projection_id": "finance.default.v1", "label": "Finance"},
            {"projection_id": "housing.default.v1", "label": "Housing"},
        ],
    }
    left_runtime = {
        "release_fingerprint": "sha256:shared",
        "projection_catalog": {
            "catalog_version": "sha256:catalog-shared",
            "release_fingerprint": "sha256:shared",
            "projections": [
                {"projection_id": "housing.default.v1", "label": "Housing"},
                {"projection_id": "finance.default.v1", "label": "Finance"},
            ],
        },
    }
    right_runtime = {
        "release_fingerprint": "sha256:shared",
        "projection_catalog": {
            "catalog_version": "sha256:catalog-shared",
            "release_fingerprint": "sha256:shared",
            "projections": [
                {"projection_id": "finance.default.v1", "label": "Finance"},
                {"projection_id": "housing.default.v1", "label": "Housing"},
            ],
        },
    }

    assert normalize_phase0_release_payload(left_release) == normalize_phase0_release_payload(right_release)
    assert normalize_phase0_runtime_payload(left_runtime) == normalize_phase0_runtime_payload(right_runtime)


def test_phase0_normalization_keeps_release_fingerprint_drift_visible() -> None:
    left_release = {
        "created_at": "2026-04-04T08:00:00Z",
        "fingerprint": "sha256:left",
        "projection_ids": ["finance.default.v1"],
        "projections": [{"projection_id": "finance.default.v1", "label": "Finance"}],
    }
    right_release = {
        "created_at": "2026-04-04T09:00:00Z",
        "fingerprint": "sha256:right",
        "projection_ids": ["finance.default.v1"],
        "projections": [{"projection_id": "finance.default.v1", "label": "Finance"}],
    }

    assert normalize_phase0_release_payload(left_release) != normalize_phase0_release_payload(right_release)


def test_phase0_normalization_keeps_runtime_release_fingerprint_drift_visible() -> None:
    left_runtime = {
        "release_fingerprint": "sha256:left",
        "projection_catalog": {
            "catalog_version": "sha256:catalog-shared",
            "release_fingerprint": "sha256:left",
            "projections": [{"projection_id": "finance.default.v1", "label": "Finance"}],
        },
    }
    right_runtime = {
        "release_fingerprint": "sha256:right",
        "projection_catalog": {
            "catalog_version": "sha256:catalog-shared",
            "release_fingerprint": "sha256:right",
            "projections": [{"projection_id": "finance.default.v1", "label": "Finance"}],
        },
    }

    assert normalize_phase0_runtime_payload(left_runtime) != normalize_phase0_runtime_payload(right_runtime)


def test_phase0_normalization_keeps_runtime_catalog_version_drift_visible() -> None:
    left_runtime = {
        "release_fingerprint": "sha256:shared",
        "projection_catalog": {
            "catalog_version": "sha256:catalog-left",
            "release_fingerprint": "sha256:shared",
            "projections": [{"projection_id": "finance.default.v1", "label": "Finance"}],
        },
    }
    right_runtime = {
        "release_fingerprint": "sha256:shared",
        "projection_catalog": {
            "catalog_version": "sha256:catalog-right",
            "release_fingerprint": "sha256:shared",
            "projections": [{"projection_id": "finance.default.v1", "label": "Finance"}],
        },
    }

    assert normalize_phase0_runtime_payload(left_runtime) != normalize_phase0_runtime_payload(right_runtime)
