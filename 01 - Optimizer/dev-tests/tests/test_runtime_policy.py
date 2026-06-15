from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

from ingestion_layer_vision.runtime_policy import load_runtime_policy_state
from ingestion_layer_vision.runtime_policy.validation import validate_runtime_semantic_assets

PIPELINE_ROOT = Path(__file__).resolve().parents[3]
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from tools.phase4_locale_test_support import build_locale_runtime_artifacts


def _fixture_payload() -> dict[str, object]:
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "runtime_semantic_assets_v1.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def _real_runtime_payload(tmp_path: Path, *, runtime_locale: str) -> dict[str, object]:
    _project_root, _release, runtime_payload = build_locale_runtime_artifacts(tmp_path, runtime_locale=runtime_locale)
    return runtime_payload


@pytest.fixture(scope="module")
def en_runtime_payload(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    payload_root = tmp_path_factory.mktemp("runtime_policy_en")
    return _strip_legacy_semantic_policy(_real_runtime_payload(payload_root, runtime_locale="en"))


def test_load_runtime_policy_state_uses_ocr_only_runtime_fixture() -> None:
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "runtime_semantic_assets_v1.json"
    payload = _fixture_payload()
    bundle = payload["vision_policy_bundle"]
    state = load_runtime_policy_state(fixture_path)

    assert state.release_id == payload["release_id"]
    assert state.release_version == payload["release_version"]
    assert state.release_fingerprint == payload["release_fingerprint"]
    assert state.bundle_version == bundle["bundle_version"]
    assert state.ocr_policy.policy_version == bundle["ocr_policy"]["policy_version"]
    assert state.ocr_policy.defaults["profile_id"] == "layout_fidelity_v1"
    assert state.ocr_policy.defaults["render"]["page_image_dpi"] == 150
    assert not hasattr(state, "semantic_extraction_policy")
    assert "semantic_extraction_policy" not in bundle


def test_load_runtime_policy_state_normalizes_stale_page_image_dpi(tmp_path: Path) -> None:
    payload = _fixture_payload()
    payload["vision_policy_bundle"]["ocr_policy"]["defaults"]["render"]["page_image_dpi"] = 360
    fixture_path = tmp_path / "runtime_semantic_assets_v1.json"
    fixture_path.write_text(json.dumps(payload), encoding="utf-8")

    state = load_runtime_policy_state(fixture_path)

    assert state.ocr_policy.defaults["render"]["page_image_dpi"] == 150


def test_validate_runtime_semantic_assets_rejects_missing_root_field() -> None:
    payload = _fixture_payload()
    payload.pop("schema_version")

    with pytest.raises(ValueError, match="runtime_semantic_assets unvollstaendig"):
        validate_runtime_semantic_assets(payload)


def test_validate_runtime_semantic_assets_rejects_missing_bundle() -> None:
    payload = _fixture_payload()
    payload.pop("vision_policy_bundle")

    with pytest.raises(ValueError, match="runtime_semantic_assets unvollstaendig"):
        validate_runtime_semantic_assets(payload)


def test_validate_runtime_semantic_assets_rejects_invalid_policy_shape() -> None:
    payload = _fixture_payload()
    payload["vision_policy_bundle"]["ocr_policy"]["defaults"] = []

    with pytest.raises(ValueError, match="vision_policy_bundle.ocr_policy.defaults"):
        validate_runtime_semantic_assets(payload)


def test_validate_runtime_semantic_assets_rejects_fingerprint_mismatch() -> None:
    payload = _fixture_payload()
    payload["vision_policy_bundle"]["release_fingerprint"] = "sha256:other"

    with pytest.raises(ValueError, match="vision_policy_bundle.release_fingerprint"):
        validate_runtime_semantic_assets(payload)


def test_validate_runtime_semantic_assets_rejects_unknown_ocr_profile() -> None:
    payload = _fixture_payload()
    payload["vision_policy_bundle"]["ocr_policy"]["defaults"]["profile_id"] = "broken_profile"

    with pytest.raises(ValueError, match="profile_id"):
        validate_runtime_semantic_assets(payload)


def test_validate_runtime_semantic_assets_rejects_local_ocr_plugin() -> None:
    payload = _fixture_payload()
    payload["vision_policy_bundle"]["ocr_policy"]["defaults"]["ocr_plugin"]["preferred_plugin"] = "ocr-paddleocr-gpu"

    with pytest.raises(ValueError, match="optimizer-llm-ocr"):
        validate_runtime_semantic_assets(payload)


def test_validate_runtime_semantic_assets_rejects_local_ocr_runtime_leftovers() -> None:
    payload = _fixture_payload()
    payload["vision_policy_bundle"]["ocr_policy"]["defaults"]["device_policy"] = {"device": "gpu:0"}

    with pytest.raises(ValueError, match="lokale OCR-Altlasten"):
        validate_runtime_semantic_assets(payload)


def test_validate_runtime_semantic_assets_rejects_semantic_policy_in_bundle() -> None:
    payload = _fixture_payload()
    payload["vision_policy_bundle"]["semantic_extraction_policy"] = {
        "policy_version": "semantic_extraction_policy_v2",
        "source_mode": "legacy",
        "defaults": {},
    }

    with pytest.raises(ValueError, match="unbekannte Felder: semantic_extraction_policy"):
        validate_runtime_semantic_assets(payload)


def test_validate_runtime_semantic_assets_accepts_real_locale_bundle_metadata(en_runtime_payload: dict[str, object]) -> None:
    payload = copy.deepcopy(en_runtime_payload)

    validated = validate_runtime_semantic_assets(payload)

    assert validated["runtime_locale"] == "en"
    assert validated["master_taxonomy_release_id"].startswith("sha256:")
    assert validated["projection_catalog"]["runtime_locale"] == "en"
    assert validated["projection_catalog"]["master_taxonomy_release_id"] == validated["master_taxonomy_release_id"]


@pytest.mark.parametrize(
    ("path", "value", "match"),
    [
        (("runtime_locale",), "de", "runtime_semantic_assets.runtime_locale"),
        (("projection_catalog", "runtime_locale"), "", "projection_catalog.runtime_locale"),
        (("master_taxonomy_release_id",), "sha256:other-master-line", "projection_catalog.master_taxonomy_release_id"),
        (("projection_catalog", "master_taxonomy_release_id"), "", "projection_catalog.master_taxonomy_release_id"),
    ],
)
def test_validate_runtime_semantic_assets_rejects_optional_locale_metadata_mismatch(
    en_runtime_payload: dict[str, object],
    path: tuple[str, ...],
    value: object,
    match: str,
) -> None:
    payload = copy.deepcopy(en_runtime_payload)
    _set_path(payload, path, value)

    with pytest.raises(ValueError, match=match):
        validate_runtime_semantic_assets(payload)


def _strip_legacy_semantic_policy(payload: dict[str, object]) -> dict[str, object]:
    cleaned = copy.deepcopy(payload)
    bundle = cleaned.get("vision_policy_bundle")
    if isinstance(bundle, dict):
        bundle.pop("semantic_extraction_policy", None)
        ocr_policy = bundle.get("ocr_policy")
        if isinstance(ocr_policy, dict):
            ocr_policy.pop("projection_overrides", None)
    return cleaned


def _set_path(payload: dict[str, object], path: tuple[str, ...], value: object) -> None:
    cursor: object = payload
    for segment in path[:-1]:
        cursor = cursor[segment]
    cursor[path[-1]] = value
