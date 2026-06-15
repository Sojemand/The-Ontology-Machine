from __future__ import annotations

from .tool_handler_deps import *


def create_locale_scaffold(arguments: dict[str, Any]) -> dict[str, Any]:
    artifact_path = Path(_required_text(arguments, "artifact_folder")).expanduser().resolve()
    payload = {
        "action": "create_locale_scaffold",
        "source_locale": _required_text(arguments, "source_locale"),
        "target_locale": _required_text(arguments, "target_locale"),
    }
    if "overwrite_existing" in arguments:
        payload["overwrite_existing"] = _optional_bool(arguments, "overwrite_existing", default=False)
    result = _invoke_workspace_normalizer_edit(artifact_path, payload)
    return {
        **result,
        "artifact_folder": str(artifact_path),
        "normalizer_authoring_home": str(_workspace_normalizer_home(artifact_path)),
        "authoring_scope": "workspace",
    }


__all__ = [name for name in globals() if not name.startswith("__")]
