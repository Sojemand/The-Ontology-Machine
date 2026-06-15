"""Workflow for ordered rendering runtime health checks."""
from __future__ import annotations

from . import runtime_checks
from .types import RendererDependencyCheck, RendererHealthSummary

_SKIPPED_PIPELINE_RUN_DETAIL = "Nicht fuer aktuellen pipeline_run benoetigt."


def renderer_dependency_selftests(
    *,
    scope: str = "",
    required_dependencies: tuple[str, ...] | None = None,
    timeout_seconds: int = runtime_checks.DEFAULT_OFFICE_SELFTEST_TIMEOUT_SECONDS,
) -> list[dict[str, object]]:
    return [
        check.to_payload()
        for check in _collect_renderer_checks(
            scope=scope,
            required_dependencies=required_dependencies,
            timeout_seconds=timeout_seconds,
        )
    ]


def renderer_selftest(*, scope: str = "") -> tuple[bool, str]:
    summary = _summarize_renderer_checks(
        _collect_renderer_checks(
            scope=scope,
            required_dependencies=None,
            timeout_seconds=runtime_checks.DEFAULT_OFFICE_SELFTEST_TIMEOUT_SECONDS,
        )
    )
    return summary.healthy, summary.detail


def _collect_renderer_checks(
    *,
    scope: str,
    required_dependencies: tuple[str, ...] | None,
    timeout_seconds: int,
) -> list[RendererDependencyCheck]:
    checks: list[RendererDependencyCheck] = []
    requested = set(required_dependencies or ())
    explicit_dependencies = required_dependencies is not None
    for probe in runtime_checks.renderer_runtime_probes(scope=scope, timeout_seconds=timeout_seconds):
        if explicit_dependencies and probe.name not in requested:
            checks.append(
                RendererDependencyCheck(
                    name=probe.name,
                    kind=probe.kind,
                    required=False,
                    healthy=True,
                    detail=_SKIPPED_PIPELINE_RUN_DETAIL,
                )
            )
            continue
        healthy, detail = probe.run()
        checks.append(
            RendererDependencyCheck(
                name=probe.name,
                kind=probe.kind,
                required=probe.required if not explicit_dependencies else True,
                healthy=bool(healthy),
                detail=str(detail),
            )
        )
    return checks


def _summarize_renderer_checks(checks: list[RendererDependencyCheck]) -> RendererHealthSummary:
    overall = all(check.healthy for check in checks if check.required)
    detail = "; ".join(f"{check.name}: {check.detail}" for check in checks)
    return RendererHealthSummary(healthy=overall, detail=detail)
