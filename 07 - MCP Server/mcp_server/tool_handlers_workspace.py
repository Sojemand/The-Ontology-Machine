from __future__ import annotations

from .tool_handler_deps import *


def prepare_pipeline_workspace_root(arguments: dict[str, Any]) -> dict[str, Any]:
    unknown = sorted(set(arguments) - {"artifact_folder"})
    if unknown:
        raise ToolFailure(f"prepare_pipeline_workspace_root kennt diese Argumente nicht: {', '.join(unknown)}")
    artifact_path = Path(_required_text(arguments, "artifact_folder")).expanduser().resolve()
    created_dirs = _ensure_pipeline_artifact_structure(artifact_path)
    return {
        "status": "ok",
        "artifact_folder": str(artifact_path),
        "input_folder": str(artifact_path / "Input"),
        "corpus_output_folder": str(artifact_path / "Corpus"),
        "documents_folder": str(artifact_path / "Documents"),
        "error_cases_folder": str(artifact_path / "Error Cases"),
        "created_dirs": created_dirs,
    }


__all__ = [name for name in globals() if not name.startswith("__")]
