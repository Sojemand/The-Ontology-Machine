from __future__ import annotations

from pathlib import Path

from orchestrator.integrations import ModuleHealthStatus, ReleaseActivationStageResult
from tests.pipeline_fake_modules import FakeModules
from tests.pipeline_harness import route_root


def assert_no_route_artifacts(ui_state) -> None:
    route = route_root(ui_state)
    assert list((route / "raw_extracts").rglob("*.*")) == []
    assert list((route / "page_images").rglob("*.*")) == []
    assert list((route / "requests").rglob("*.*")) == []
    assert list((route / "structured").rglob("*.*")) == []
    assert list((route / "validation").rglob("*.*")) == []
    assert list((route / "normalized").rglob("*.*")) == []
    assert list((route / "originals").rglob("*.*")) == []
    assert list((route / "logs").rglob("*.*")) == []


class ReleaseAwareModules(FakeModules):
    def __init__(self) -> None:
        super().__init__({})
        self.release_active = False
        self.release_events: list[tuple[str, object]] = []

    def activate_semantic_release(
        self,
        release_path: Path,
        corpus_db_path: Path,
        confirmation_artifact_path: Path | None = None,
    ) -> ReleaseActivationStageResult:
        self.release_events.append(("activate", str(release_path), str(confirmation_artifact_path or "")))
        self.release_active = True
        return ReleaseActivationStageResult(
            status="applied",
            reason="",
            release_id="semantic_release.test",
            release_version="v1",
            active_snapshot_id="sha256:test-snapshot",
        )

    def healthcheck(
        self,
        *,
        module_keys: tuple[str, ...] | None = None,
        scope: str = "pipeline_run",
        required_dependencies_by_module: dict[str, tuple[str, ...]] | None = None,
        corpus_db_path: Path | None = None,
    ) -> list[ModuleHealthStatus]:
        self.healthcheck_calls.append((module_keys, scope, required_dependencies_by_module, str(corpus_db_path) if corpus_db_path is not None else ""))
        self.release_events.append(("healthcheck", module_keys or ()))
        return [ModuleHealthStatus(key=key, display_name=key, healthy=True, message="") for key in (module_keys or ())]

    def activation_preflight(self, release_path: Path, corpus_db_path: Path) -> dict[str, object]:
        self.release_events.append(("preflight", str(release_path), str(corpus_db_path)))
        if self.release_active:
            return {
                "current_snapshot": {"snapshot_id": "sha256:test-snapshot"},
                "next_snapshot": {"snapshot_id": "sha256:test-snapshot"},
                "db_changes": {"projection_drift_documents": 0, "stale_documents_after_activation": 0},
                "requires_confirmation": False,
                "initialization_required": False,
                "no_op": True,
            }
        return {
            "current_snapshot": {"snapshot_id": "sha256:old-snapshot"},
            "next_snapshot": {"snapshot_id": "sha256:test-snapshot"},
            "db_changes": {"projection_drift_documents": 1, "stale_documents_after_activation": 1},
            "runtime_locale": {
                "current": {"value": "en", "provenance": "release"},
                "next": {"value": "en", "provenance": "release"},
            },
            "requires_confirmation": True,
            "initialization_required": False,
            "confirmation_artifact_template": confirmation_template(release_path, corpus_db_path),
            "no_op": False,
        }

    def read_active_semantic_release(self, corpus_db_path: Path) -> dict[str, object]:
        self.release_events.append(("read_active", str(corpus_db_path)))
        if not self.release_active:
            raise RuntimeError("Active semantic release is missing")
        return super().read_active_semantic_release(corpus_db_path)

    def build_runtime_semantic_assets(self, release: dict[str, object]) -> dict[str, object]:
        self.release_events.append(("build_runtime_assets", str(release.get("fingerprint", ""))))
        return super().build_runtime_semantic_assets(release)


class ReleaseFailingModules(FakeModules):
    def __init__(self, reason: str) -> None:
        super().__init__({})
        self.reason = reason
        self.release_events: list[tuple[str, object]] = []

    def activate_semantic_release(
        self,
        release_path: Path,
        corpus_db_path: Path,
        confirmation_artifact_path: Path | None = None,
    ) -> ReleaseActivationStageResult:
        del corpus_db_path, confirmation_artifact_path
        self.release_events.append(("activate", str(release_path)))
        return ReleaseActivationStageResult(status="error", reason=self.reason, release_id="", release_version="")


def confirmation_template(release_path: Path, corpus_db_path: Path) -> dict[str, object]:
    return {
        "artifact_version": "semantic_activation_confirmation_v1",
        "corpus_db_path": str(corpus_db_path),
        "release_path": str(release_path),
        "expected_current_snapshot_id": "sha256:old-snapshot",
        "expected_new_snapshot_id": "sha256:test-snapshot",
        "expected_release_fingerprint": "sha256:semantic-default",
        "expected_master_taxonomy_release_id": "sha256:master-line",
        "expected_runtime_locale": "en",
        "decision": "activate_only",
    }
