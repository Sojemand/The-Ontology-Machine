"""Vision-profile healthcheck workflow for the optimizer contract."""
from __future__ import annotations

from pathlib import Path

from optimizer_ocr import check_readiness

from ..paths import ensure_app_layout
from . import validation

_OPTIMIZER_OCR_DEPENDENCY = "optimizer_ocr"


def run(
    payload: dict,
    *,
    root: Path,
    app_home: Path | None,
    load_config,
    plugin_manager_cls,
) -> dict:
    layout = ensure_app_layout(module_root_path=root, app_home_path=app_home)
    config = load_config(layout.default_config_path)
    plugin_mgr = plugin_manager_cls(layout.plugins_dir, config)
    try:
        return _build_response(payload, plugin_mgr)
    finally:
        plugin_mgr.kill_all()


def _build_response(payload: dict, plugin_mgr) -> dict:
    checks = (
        ("pdf-pdfplumber", "runtime"),
        (_OPTIMIZER_OCR_DEPENDENCY, "llm"),
    )
    required_names = validation.required_healthcheck_dependencies(payload)
    dependencies = []
    overall_healthy = True
    for name, kind in checks:
        healthy, detail = _dependency_status(name, plugin_mgr)
        required = name in required_names
        dependencies.append(_dependency(name, kind, required, healthy, detail))
        if required and not healthy:
            overall_healthy = False
    return {
        "status": "ok" if overall_healthy else "error",
        "healthy": overall_healthy,
        "message": "" if overall_healthy else "Core-Extraktoren des Optimizers sind nicht verfuegbar.",
        "dependencies": dependencies,
    }


def _dependency(name: str, kind: str, required: bool, healthy: bool, detail: str) -> dict:
    return {"name": name, "kind": kind, "required": required, "healthy": healthy, "detail": detail}


def _dependency_status(name: str, plugin_mgr) -> tuple[bool, str]:
    if name == _OPTIMIZER_OCR_DEPENDENCY:
        return check_readiness()
    return plugin_mgr.selftest(name)
