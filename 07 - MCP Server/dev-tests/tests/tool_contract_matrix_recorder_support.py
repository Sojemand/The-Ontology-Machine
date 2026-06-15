from __future__ import annotations

from typing import Any


class _FakeProcess:
    pid = 4242
    returncode = 0

    def poll(self) -> None:
        return None

    def terminate(self) -> None:
        self.returncode = 0

    def wait(self, timeout: float | None = None) -> int:
        return self.returncode

    def communicate(self, input: str | None = None, timeout: float | None = None) -> tuple[str, str]:
        return ("", "")

    def kill(self) -> None:
        self.returncode = 1

    def __enter__(self) -> "_FakeProcess":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def _active_release_payload() -> dict[str, Any]:
    return {
        "release_id": "semantic_release.test",
        "release_version": "1.0.0",
        "master_taxonomy_id": "taxonomy.master",
        "master_taxonomy_version": "1",
        "projection_ids": ["finance.default.v1"],
        "materialization_version": "1",
        "fingerprint": "sha256:test-release",
        "master_taxonomy": {"axes": {}},
        "projections": [{
            "projection_id": "finance.default.v1",
            "label": "Finance",
            "routing": {
                "when_to_use": "finance documents",
                "avoid_when": "non-finance documents",
                "example_document_types": ["invoice"],
                "surface_signals": {"text_markers": [], "domain_markers": [], "section_roles": [], "party_roles": []},
            },
        }],
        "runtime_locale": "de",
    }
