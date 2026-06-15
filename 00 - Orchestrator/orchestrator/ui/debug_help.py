"""Module-specific help texts for the orchestrator debug host."""

from __future__ import annotations

from .debug_help_corpus_builder import HELP_ENTRIES as _CORPUS_BUILDER_HELP_ENTRIES
from .debug_help_interpreters import HELP_ENTRIES as _INTERPRETER_HELP_ENTRIES
from .debug_help_optimizers import HELP_ENTRIES as _OPTIMIZER_HELP_ENTRIES
from .debug_help_validator import HELP_ENTRIES as _VALIDATOR_HELP_ENTRIES

_HELP_ENTRIES = {
    **_CORPUS_BUILDER_HELP_ENTRIES,
    **_OPTIMIZER_HELP_ENTRIES,
    **_INTERPRETER_HELP_ENTRIES,
    **_VALIDATOR_HELP_ENTRIES,
}


def get_help(module_key: str) -> tuple[str, str] | None:
    return _HELP_ENTRIES.get(str(module_key or "").strip().lower())


def has_help(module_key: str) -> bool:
    return get_help(module_key) is not None
