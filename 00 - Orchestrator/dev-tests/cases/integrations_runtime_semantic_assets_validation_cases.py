from __future__ import annotations

from typing import Any

import pytest

from orchestrator.integrations.runtime_semantic_assets import build_runtime_semantic_assets
from orchestrator.integrations.types import ModuleContractError

from .integrations_runtime_semantic_assets_support import _release_payload, _runtime_assets, _set_path


def test_build_runtime_semantic_assets_rejects_fingerprint_mismatch() -> None:
    class Modules:
        def build_runtime_semantic_assets(self, release: dict[str, object]) -> dict[str, object]:
            assets = _runtime_assets(release)
            assets["vision_policy_bundle"]["release_fingerprint"] = "sha256:other"
            return {"status": "OK", "runtime_semantic_assets": assets}

    with pytest.raises(ModuleContractError, match="vision_policy_bundle.release_fingerprint"):
        build_runtime_semantic_assets(Modules(), release=_release_payload())


@pytest.mark.parametrize(
    ("path", "value", "match"),
    [
        (("release_id",), "semantic_release.other", "runtime_semantic_assets.release_id"),
        (("release_version",), "2", "runtime_semantic_assets.release_version"),
        (("release_fingerprint",), "sha256:other", "runtime_semantic_assets.release_fingerprint"),
        (("master_taxonomy_id",), "taxonomy.other", "runtime_semantic_assets.master_taxonomy_id"),
        (("master_taxonomy_version",), "2026-04-03.v1", "runtime_semantic_assets.master_taxonomy_version"),
        (("master_taxonomy_release_id",), "sha256:other-master-line", "runtime_semantic_assets.master_taxonomy_release_id"),
        (("runtime_locale",), "de", "runtime_semantic_assets.runtime_locale"),
        (("projection_catalog", "release_id"), "semantic_release.other", "projection_catalog.release_id"),
        (("projection_catalog", "release_version"), "2", "projection_catalog.release_version"),
        (("projection_catalog", "release_fingerprint"), "sha256:other", "projection_catalog.release_fingerprint"),
        (("projection_catalog", "master_taxonomy_id"), "taxonomy.other", "projection_catalog.master_taxonomy_id"),
        (("projection_catalog", "master_taxonomy_version"), "2026-04-03.v1", "projection_catalog.master_taxonomy_version"),
        (("projection_catalog", "master_taxonomy_release_id"), "sha256:other-master-line", "projection_catalog.master_taxonomy_release_id"),
        (("projection_catalog", "runtime_locale"), "de", "projection_catalog.runtime_locale"),
    ],
)
def test_build_runtime_semantic_assets_rejects_release_consistency_mismatch(
    path: tuple[str, ...],
    value: Any,
    match: str,
) -> None:
    class Modules:
        def build_runtime_semantic_assets(self, release: dict[str, object]) -> dict[str, object]:
            assets = _runtime_assets(release)
            _set_path(assets, path, value)
            return {"status": "OK", "runtime_semantic_assets": assets}

    with pytest.raises(ModuleContractError, match=match):
        build_runtime_semantic_assets(Modules(), release=_release_payload())
