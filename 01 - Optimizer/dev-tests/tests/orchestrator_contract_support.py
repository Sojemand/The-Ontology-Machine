"""Shared stubs for orchestrator contract tests."""
from __future__ import annotations

import copy
import json
import uuid
from pathlib import Path
from types import SimpleNamespace


class DummyPluginManager:
    def __init__(self, outcomes: dict[str, tuple[bool, str]]) -> None:
        self._outcomes = outcomes
        self.calls: list[str] = []

    def selftest(self, name: str, *args, **kwargs) -> tuple[bool, str]:
        del args, kwargs
        self.calls.append(name)
        if name not in self._outcomes:
            raise AssertionError(f"unexpected selftest: {name}")
        return self._outcomes[name]

    def kill_all(self) -> None:
        self.calls.append("kill_all")


def debug_single_processor(captured: dict[str, object], *, capture_init_kwargs: bool = False):
    class DummyProcessor:
        def __init__(self, config, *_args, **_kwargs):
            captured["config"] = config
            if capture_init_kwargs:
                captured["init_kwargs"] = dict(_kwargs)

        def process_single(self, source_path, **kwargs):
            captured["source_path"] = source_path
            captured["kwargs"] = kwargs
            kwargs["raw_output_path"].parent.mkdir(parents=True, exist_ok=True)
            kwargs["raw_output_path"].write_text("{}", encoding="utf-8")
            kwargs["page_assets_dir"].mkdir(parents=True, exist_ok=True)
            (kwargs["page_assets_dir"] / "page_001.png").write_text("png", encoding="utf-8")
            return [stub_extract()]

        def cancel(self) -> None:
            captured["cancelled"] = True

    return DummyProcessor


def stub_extract(*, content_hash: str = "sha256:" + "ab" * 32, ingest_id: str | None = None):
    return SimpleNamespace(
        source=SimpleNamespace(content_hash=content_hash, ingest_id=ingest_id or str(uuid.uuid4())),
        image_paths=[],
    )


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "runtime_semantic_assets_v1.json"


def runtime_policy_payload() -> dict[str, object]:
    return copy.deepcopy(json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))
