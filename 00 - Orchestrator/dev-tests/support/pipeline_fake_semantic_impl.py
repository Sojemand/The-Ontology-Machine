from __future__ import annotations

from pathlib import Path

from support.pipeline_fake_semantic_defaults import (
    default_activation_preflight,
    default_active_snapshot,
    default_release,
    default_runtime_semantic_assets,
)


class PipelineFakeSemanticMixin:
    def build_projection_catalog(self) -> dict[str, object]:
        configured = self.scenarios.get("__projection_catalog__", {})
        if isinstance(configured, dict) and configured:
            return dict(configured)
        release = default_release()
        return {
            "catalog_version": "sha256:test",
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
        self.runtime_semantic_release_reads.append(str(corpus_db_path))
        configured = self.scenarios.get("__active_release__", {})
        if isinstance(configured, dict) and configured:
            return dict(configured)
        release = default_release()
        active_snapshot = default_active_snapshot(corpus_db_path, release)
        return {
            "status": {"active_release_id": release["release_id"]},
            "release": dict(release),
            "release_id": release["release_id"],
            "release_version": release["release_version"],
            "fingerprint": release["fingerprint"],
            "release_path": str(corpus_db_path.parent / "semantic_release.active.json"),
            "master_taxonomy_release_id": release["master_taxonomy_release_id"],
            "runtime_locale": release["runtime_locale"],
            "active_snapshot": active_snapshot,
        }

    def activation_preflight(self, release_path: Path, corpus_db_path: Path) -> dict[str, object]:
        self.release_preflight_calls.append((str(release_path), str(corpus_db_path)))
        configured = self.scenarios.get("__activation_preflight__", {})
        if isinstance(configured, dict) and configured:
            return dict(configured)
        return default_activation_preflight(corpus_db_path, release_path)

    def build_runtime_semantic_assets(self, release: dict[str, object]) -> dict[str, object]:
        self.runtime_semantic_asset_builds.append(str(release.get("fingerprint", "")))
        configured = self.scenarios.get("__runtime_semantic_assets__", {})
        if isinstance(configured, dict) and configured:
            return dict(configured)
        return {"status": "OK", "runtime_semantic_assets": default_runtime_semantic_assets(release)}
