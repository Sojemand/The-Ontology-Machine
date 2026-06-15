from __future__ import annotations

from pathlib import Path

from orchestrator.integrations import EmbeddingStageResult, ModuleHealthStatus, ReleaseActivationStageResult

HEALTH_DISPLAY = {
    "optimizer": "Optimizer",
    "optimizer": "Optimizer",
    "interpreter": "Interpreter",
    "interpreter": "Interpreter",
    "validator": "Validator",
    "normalizer": "Normalizer",
    "corpus_builder": "Corpus Builder",
}


class FixtureReplayModuleSupport:
    def close(self) -> None:
        return None

    def build_projection_catalog(self) -> dict[str, object]:
        release = _fixture_release()
        return {
            "catalog_version": "sha256:fixture",
            "release_id": str(release["release_id"]),
            "release_version": str(release["release_version"]),
            "release_fingerprint": str(release["fingerprint"]),
            "master_taxonomy_id": str(release["master_taxonomy_id"]),
            "master_taxonomy_version": str(release["master_taxonomy_version"]),
            "master_taxonomy_release_id": str(release["master_taxonomy_release_id"]),
            "runtime_locale": str(release["runtime_locale"]),
            "projections": [],
        }

    def read_active_semantic_release(self, corpus_db_path: Path) -> dict[str, object]:
        release = _fixture_release()
        runtime_assets = self.build_runtime_semantic_assets(release)["runtime_semantic_assets"]
        return {
            "status": {"active_release_id": release["release_id"]},
            "release": release,
            "release_id": release["release_id"],
            "release_version": release["release_version"],
            "fingerprint": release["fingerprint"],
            "release_path": str(corpus_db_path.parent / "semantic_release.active.json"),
            "master_taxonomy_release_id": release["master_taxonomy_release_id"],
            "runtime_locale": release["runtime_locale"],
            "active_snapshot": {
                "snapshot_id": "sha256:fixture-snapshot",
                "release": {**release, "active_snapshot": {"snapshot_id": "sha256:fixture-snapshot", "release_path": str(corpus_db_path.parent / "semantic_release.active.json")}},
                "projection_catalog": dict(runtime_assets["projection_catalog"]),
                "runtime_semantic_assets": runtime_assets,
                "master_taxonomy_release_id": release["master_taxonomy_release_id"],
                "runtime_locale": release["runtime_locale"],
                "release_path": str(corpus_db_path.parent / "semantic_release.active.json"),
            },
        }

    def build_runtime_semantic_assets(self, release: dict[str, object]) -> dict[str, object]:
        fingerprint = str(release.get("fingerprint") or "")
        projection_catalog = {
            "catalog_version": "sha256:fixture-runtime",
            "release_id": str(release.get("release_id") or ""),
            "release_version": str(release.get("release_version") or ""),
            "release_fingerprint": fingerprint,
            "master_taxonomy_id": str(release.get("master_taxonomy_id") or ""),
            "master_taxonomy_version": str(release.get("master_taxonomy_version") or ""),
            "master_taxonomy_release_id": str(release.get("master_taxonomy_release_id") or ""),
            "runtime_locale": str(release.get("runtime_locale") or ""),
            "projections": [],
        }
        return {
            "status": "OK",
            "runtime_semantic_assets": {
                "schema_version": "runtime_semantic_assets_v1",
                "release_id": str(release.get("release_id") or ""),
                "release_version": str(release.get("release_version") or ""),
                "release_fingerprint": fingerprint,
                "master_taxonomy_id": str(release.get("master_taxonomy_id") or ""),
                "master_taxonomy_version": str(release.get("master_taxonomy_version") or ""),
                "master_taxonomy_release_id": str(release.get("master_taxonomy_release_id") or ""),
                "runtime_locale": str(release.get("runtime_locale") or ""),
                "projection_catalog": projection_catalog,
                "vision_policy_bundle": {
                    "bundle_version": "vision_policy_bundle_v1",
                    "release_fingerprint": fingerprint,
                    "ocr_policy": {
                        "policy_version": "ocr_policy_v1",
                        "source_mode": "legacy_defaults",
                        "defaults": {},
                        "projection_overrides": {},
                    },
                    "semantic_extraction_policy": {
                        "policy_version": "semantic_extraction_policy_v1",
                        "source_mode": "legacy_defaults",
                        "defaults": {},
                        "projection_overrides": {},
                    },
                },
            },
        }

    def activate_semantic_release(
        self,
        release_path: Path,
        corpus_db_path: Path,
        confirmation_artifact_path: Path | None = None,
    ) -> ReleaseActivationStageResult:
        del release_path, corpus_db_path, confirmation_artifact_path
        return ReleaseActivationStageResult(
            status="applied",
            reason="",
            release_id="fixture-release",
            release_version="v1",
            active_snapshot_id="sha256:fixture-snapshot",
        )

    def generate_embeddings(self, corpus_db_path: Path, *, force_enable: bool = False) -> EmbeddingStageResult:
        step = self._next("embeddings")
        return EmbeddingStageResult(status=str(step["status"]), count=int(step.get("count", 0)), reason=str(step.get("reason", "")))

    def healthcheck(
        self,
        *,
        module_keys: tuple[str, ...] | None = None,
        scope: str = "pipeline_run",
        required_dependencies_by_module: dict[str, tuple[str, ...]] | None = None,
        corpus_db_path: Path | None = None,
    ) -> list[ModuleHealthStatus]:
        del scope, required_dependencies_by_module, corpus_db_path
        return [ModuleHealthStatus(key=key, display_name=HEALTH_DISPLAY.get(key, key), healthy=True, message="") for key in (module_keys or tuple(HEALTH_DISPLAY))]

    def _next(self, stage: str) -> dict:
        if stage not in self._stages:
            raise AssertionError(f"Unexpected stage call: {stage}")
        value = self._stages[stage]
        if isinstance(value, list):
            index = self._indexes.get(stage, 0)
            self._indexes[stage] = index + 1
            return value[index if index < len(value) else -1]
        return value


def _fixture_release() -> dict[str, object]:
    return {
        "release_id": "fixture-release",
        "release_version": "v1",
        "master_taxonomy_id": "fixture-taxonomy",
        "master_taxonomy_version": "fixture.v1",
        "master_taxonomy_release_id": "sha256:fixture-master-line",
        "runtime_locale": "en",
        "projection_ids": [],
        "materialization_version": "fixture.materialization",
        "fingerprint": "sha256:fixture-release",
        "master_taxonomy": {"taxonomy_id": "fixture-taxonomy"},
        "projections": [],
    }

