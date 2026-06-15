from __future__ import annotations

from tests.pipeline_harness import route_root

def _assert_no_route_artifacts(ui_state) -> None:
    route = route_root(ui_state)
    assert list((route / "raw_extracts").rglob("*.*")) == []
    assert list((route / "page_images").rglob("*.*")) == []
    assert list((route / "structured").rglob("*.*")) == []
    assert list((route / "validation").rglob("*.*")) == []
    assert list((route / "normalized").rglob("*.*")) == []
    assert list((route / "originals").rglob("*.*")) == []
    assert list((route / "logs").rglob("*.*")) == []
