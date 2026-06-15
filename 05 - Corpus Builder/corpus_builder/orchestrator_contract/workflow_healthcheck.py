"""Healthcheck helpers for the Corpus Builder subprocess contract."""
from __future__ import annotations

from ..context import ModuleContext
from ..embeddings import check_api_available, resolve_runtime_capability, sanitize_reason
from ..services.semantic_status_context import inspect_release


def healthcheck(command, *, context: ModuleContext) -> dict:
    pipeline_healthy, pipeline_message = _pipeline_release_health(command, context)
    dependencies: list[dict[str, object]] = []
    capability = resolve_runtime_capability()
    if capability.status != "available":
        dependencies.append({"name": "embedding_provider", "kind": "service", "required": False, "healthy": False, "detail": capability.reason})
        return {"status": "ok", "healthy": pipeline_healthy, "message": pipeline_message, "dependencies": dependencies}
    healthy, detail = check_api_available(
        capability.api_key,
        model=command.runtime_settings.model,
        base_url=getattr(capability, "base_url", None),
        provider_family=getattr(capability, "provider_family", None),
    )
    dependencies.append({"name": "embedding_provider", "kind": "service", "required": False, "healthy": healthy, "detail": sanitize_reason(detail)})
    return {"status": "ok", "healthy": pipeline_healthy, "message": pipeline_message, "dependencies": dependencies}


def _pipeline_release_health(command, context: ModuleContext) -> tuple[bool, str]:
    if command.scope != "pipeline_run" or not isinstance(context, ModuleContext):
        return True, ""
    try:
        release, _active_snapshot, _release_path, _runtime_truth_source = inspect_release(
            context,
            corpus_db_path=getattr(command, "corpus_db_path", None),
        )
        if release is None:
            raise ValueError(
                "Kein aktiver Semantic Release vorhanden. Wende zuerst den veroeffentlichten Release an."
            )
    except ValueError as exc:
        detail = str(exc).strip()
        hint = (
            "Ein aktiver Semantic Release ist fuer den Pipeline-Start zwingend, "
            "weil der Corpus Builder normalized Dokumente gegen die aktive Projektion "
            "materialisiert. Waehle im Orchestrator eine Semantic-Release-Datei oder "
            "installiere und aktiviere den mitgelieferten Release im Corpus Builder."
        )
        return False, f"{detail} {hint}".strip()
    return True, ""
