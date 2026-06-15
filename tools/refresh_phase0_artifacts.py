from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PIPELINE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NORMALIZER_ROOT = PIPELINE_ROOT / "04 - Normalizer"
NORMALIZER_DEV_TESTS_ROOT = DEFAULT_NORMALIZER_ROOT / "dev-tests"
DEFAULT_OPTIMIZER_FIXTURE_PATH = PIPELINE_ROOT / "01 - Optimizer" / "dev-tests" / "fixtures" / "runtime_semantic_assets_v1.json"
DEFAULT_CORPUS_RELEASE_PATH = PIPELINE_ROOT / "05 - Corpus Builder" / "config" / "semantic_release.default.json"
DEFAULT_CORPUS_ACTIVE_RELEASE_PATH = PIPELINE_ROOT / "05 - Corpus Builder" / "state" / "semantic_release.active.json"
DEFAULT_CORPUS_STAGE_RELEASE_PATH = PIPELINE_ROOT / "05 - Corpus Builder" / "dist" / "stage" / "config" / "semantic_release.default.json"

if str(DEFAULT_NORMALIZER_ROOT) not in sys.path:
    sys.path.insert(0, str(DEFAULT_NORMALIZER_ROOT))
if str(NORMALIZER_DEV_TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(NORMALIZER_DEV_TESTS_ROOT))

from normalizer_vision.runtime_semantic_assets import build_runtime_semantic_assets
from normalizer_vision.semantic_release import build_semantic_release
from phase0_artifact_helpers import (
    artifact_paths,
    canonical_release_payload,
    load_required_json,
    project_optimizer_runtime_payload,
    write_json_if_changed,
)
from tests.fixtures.taxonomy_refactor_baseline import normalize_phase0_release_payload, normalize_phase0_runtime_payload


def build_phase0_artifacts(normalizer_root: str | Path | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path(normalizer_root) if normalizer_root is not None else DEFAULT_NORMALIZER_ROOT
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    release_payload = build_semantic_release(root)
    runtime_payload = build_runtime_semantic_assets(release_payload).to_dict()
    return release_payload, runtime_payload


def refresh_phase0_artifacts(
    *,
    normalizer_root: str | Path | None = None,
    optimizer_fixture_path: str | Path = DEFAULT_OPTIMIZER_FIXTURE_PATH,
    corpus_release_path: str | Path = DEFAULT_CORPUS_RELEASE_PATH,
    corpus_active_release_path: str | Path = DEFAULT_CORPUS_ACTIVE_RELEASE_PATH,
    corpus_stage_release_path: str | Path = DEFAULT_CORPUS_STAGE_RELEASE_PATH,
) -> dict[str, object]:
    release_payload, runtime_payload = build_phase0_artifacts(normalizer_root)
    paths = artifact_paths(
        optimizer_fixture_path=optimizer_fixture_path,
        corpus_release_path=corpus_release_path,
        corpus_active_release_path=corpus_active_release_path,
        corpus_stage_release_path=corpus_stage_release_path,
    )
    canonical_release = canonical_release_payload(release_payload, paths["release_paths"])
    optimizer_runtime_payload = project_optimizer_runtime_payload(
        runtime_payload,
        reference_fixture_path=paths["optimizer_fixture_path"],
    )
    updated_paths: list[str] = []
    if write_json_if_changed(paths["optimizer_fixture_path"], optimizer_runtime_payload):
        updated_paths.append(str(paths["optimizer_fixture_path"]))
    for path in paths["release_paths"]:
        if write_json_if_changed(path, canonical_release):
            updated_paths.append(str(path))
    verify_phase0_artifacts(
        normalizer_root=normalizer_root,
        optimizer_fixture_path=paths["optimizer_fixture_path"],
        corpus_release_path=paths["release_paths"][0],
        corpus_active_release_path=paths["release_paths"][1],
        corpus_stage_release_path=paths["release_paths"][2],
    )
    return {
        "updated_paths": updated_paths,
        "release_fingerprint": str(canonical_release.get("fingerprint") or ""),
        "runtime_release_fingerprint": str(runtime_payload.get("release_fingerprint") or ""),
    }


def verify_phase0_artifacts(
    *,
    normalizer_root: str | Path | None = None,
    optimizer_fixture_path: str | Path = DEFAULT_OPTIMIZER_FIXTURE_PATH,
    corpus_release_path: str | Path = DEFAULT_CORPUS_RELEASE_PATH,
    corpus_active_release_path: str | Path = DEFAULT_CORPUS_ACTIVE_RELEASE_PATH,
    corpus_stage_release_path: str | Path = DEFAULT_CORPUS_STAGE_RELEASE_PATH,
) -> None:
    expected_release, expected_runtime = build_phase0_artifacts(normalizer_root)
    paths = artifact_paths(
        optimizer_fixture_path=optimizer_fixture_path,
        corpus_release_path=corpus_release_path,
        corpus_active_release_path=corpus_active_release_path,
        corpus_stage_release_path=corpus_stage_release_path,
    )
    release_payloads = [load_required_json(path) for path in paths["release_paths"]]
    expected_release_view = normalize_phase0_release_payload(expected_release)
    release_labels = ("published_release", "active_release", "staged_release")
    for label, path, payload in zip(release_labels, paths["release_paths"], release_payloads):
        if normalize_phase0_release_payload(payload) != expected_release_view:
            raise AssertionError(f"{label} drifted from the canonical 04 semantic release: {path}")
    if release_payloads[0] != release_payloads[1] or release_payloads[0] != release_payloads[2]:
        raise AssertionError("Phase-0 release mirrors are not byte-stable mirrors of the same release payload.")
    fixture_payload = load_required_json(paths["optimizer_fixture_path"])
    expected_runtime_view = project_optimizer_runtime_payload(
        expected_runtime,
        reference_fixture_path=paths["optimizer_fixture_path"],
    )
    if normalize_phase0_runtime_payload(fixture_payload) != normalize_phase0_runtime_payload(expected_runtime_view):
        raise AssertionError(f"Optimizer runtime fixture drifted from the canonical 04 runtime bundle: {paths['optimizer_fixture_path']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh and verify the phase-0 Optimizer fixture and Corpus Builder release mirrors from the canonical 04 compiler output.")
    parser.add_argument("--normalizer-root", default=str(DEFAULT_NORMALIZER_ROOT), help="Normalizer project root. Defaults to the pipeline's '04 - Normalizer' directory.")
    parser.add_argument("--optimizer-fixture-path", default=str(DEFAULT_OPTIMIZER_FIXTURE_PATH), help="Target JSON path for the checked-in 01 runtime semantic fixture.")
    parser.add_argument("--corpus-release-path", default=str(DEFAULT_CORPUS_RELEASE_PATH), help="Target JSON path for the published 05 semantic release mirror.")
    parser.add_argument("--corpus-active-release-path", default=str(DEFAULT_CORPUS_ACTIVE_RELEASE_PATH), help="Target JSON path for the active 05 semantic release mirror.")
    parser.add_argument("--corpus-stage-release-path", default=str(DEFAULT_CORPUS_STAGE_RELEASE_PATH), help="Target JSON path for the staged 05 semantic release mirror.")
    args = parser.parse_args(argv)
    result = refresh_phase0_artifacts(
        normalizer_root=args.normalizer_root,
        optimizer_fixture_path=args.optimizer_fixture_path,
        corpus_release_path=args.corpus_release_path,
        corpus_active_release_path=args.corpus_active_release_path,
        corpus_stage_release_path=args.corpus_stage_release_path,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
