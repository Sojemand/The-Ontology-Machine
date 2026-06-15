"""Runtime probes for the rendering health workflow."""
from __future__ import annotations

from . import office_runtime_probe
from .types import RendererRuntimeProbe

DEFAULT_OFFICE_SELFTEST_TIMEOUT_SECONDS = 30


def renderer_runtime_probes(
    *,
    scope: str = "",
    timeout_seconds: int = DEFAULT_OFFICE_SELFTEST_TIMEOUT_SECONDS,
) -> tuple[RendererRuntimeProbe, ...]:
    return (
        RendererRuntimeProbe(name="renderer-pdf", run=_probe_pdf_runtime),
        RendererRuntimeProbe(
            name="renderer-office",
            run=lambda: _probe_office_runtime(scope=scope, timeout_seconds=timeout_seconds),
        ),
        RendererRuntimeProbe(name="renderer-html", run=_probe_html_runtime),
    )


def _probe_pdf_runtime() -> tuple[bool, str]:
    try:
        import fitz  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError as exc:
        return False, str(exc)
    return True, "OK (fitz + Pillow)"


def _probe_office_runtime(
    *,
    scope: str = "",
    timeout_seconds: int = DEFAULT_OFFICE_SELFTEST_TIMEOUT_SECONDS,
) -> tuple[bool, str]:
    return office_runtime_probe.probe_office_runtime(scope=scope, timeout_seconds=timeout_seconds)


def _probe_html_runtime() -> tuple[bool, str]:
    try:
        import fitz
    except ImportError as exc:
        return False, str(exc)
    if "Story" not in dir(fitz):
        return False, "PyMuPDF Story API fehlt"
    return True, "OK (fitz Story + fallback renderer)"
