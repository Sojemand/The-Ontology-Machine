"""Workflow helpers for the validator subprocess contract."""
from __future__ import annotations

from .types import ValidateDocumentCommand


def error_response(message: str) -> dict:
    return {"status": "ERROR", "error": message}


def validate_document(
    command: ValidateDocumentCommand,
    *,
    load_config_fn,
    validator_cls,
) -> dict:
    try:
        validator = validator_cls(load_config_fn())
        report = validator.validate(
            command.structured_path,
            command.validation_output_path,
            raw_path=command.raw_path,
        )
    except Exception as exc:
        return error_response(f"Validierung fehlgeschlagen: {exc}")

    detail = (
        f"{report.result} "
        f"(issues={report.summary.total_issues}, "
        f"fail={report.summary.fail_count}, warn={report.summary.warn_count})"
    )
    return {
        "status": report.result,
        "report_path": str(command.validation_output_path),
        "needs_review": bool(report.needs_review),
        "detail": detail,
        "error": "",
    }


def healthcheck(*, load_config_fn=None) -> dict:
    dependencies = []
    if load_config_fn is not None:
        try:
            load_config_fn()
        except Exception as exc:
            return {
                "status": "ERROR",
                "healthy": False,
                "message": f"Config-Healthcheck fehlgeschlagen: {exc}",
                "dependencies": [_dependency_payload(healthy=False, detail=str(exc))],
            }
        dependencies.append(_dependency_payload(healthy=True, detail="ok"))
    return {
        "status": "ok",
        "healthy": True,
        "message": "",
        "dependencies": dependencies,
    }


def _dependency_payload(*, healthy: bool, detail: str) -> dict:
    return {
        "name": "config",
        "kind": "config",
        "required": True,
        "healthy": healthy,
        "detail": detail,
    }
