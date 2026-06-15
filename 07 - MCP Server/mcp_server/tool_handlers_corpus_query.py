from __future__ import annotations

from .tool_handler_deps import *
from .tool_handlers_artifact_rebuild import _corpus_optional_path_action
def generate_embeddings(arguments: dict[str, Any]) -> dict[str, Any]:
    return _invoke_product(
        "corpus_builder",
        {
            "action": "generate_embeddings",
            "corpus_db_path": _required_text(arguments, "corpus_db_path"),
            "runtime_model": _required_text(arguments, "runtime_model"),
        },
    )


def search_corpus(arguments: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "action": "search",
        "query": _required_text(arguments, "query"),
        "mode": _optional_text(arguments, "mode") or "Fulltext",
    }
    _add_optional(payload, arguments, "corpus_db_path")
    _add_optional(payload, arguments, "runtime_model")
    if "limit" in arguments and arguments["limit"] not in (None, ""):
        payload["limit"] = _positive_int(arguments["limit"], "limit")
    return _invoke_product("corpus_builder", payload)


def corpus_stats(arguments: dict[str, Any]) -> dict[str, Any]:
    return _corpus_optional_path_action("stats", arguments)


def export_corpus(arguments: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "action": "export",
        "output_path": _required_text(arguments, "output_path"),
        "fmt": _optional_text(arguments, "fmt") or "jsonl",
        "include_archived": _optional_bool(arguments, "include_archived", default=False),
    }
    _add_optional(payload, arguments, "corpus_db_path")
    return _invoke_product("corpus_builder", payload)

__all__ = [name for name in globals() if not name.startswith("__")]
