"""Shared response envelope for source-layer authoring actions."""
from __future__ import annotations

from typing import Iterable

_USED_BY_MODULES = ["02 - Interpreter", "04 - Normalizer", "05 - Corpus Builder"]
_DEFAULT_COMPILE_EFFECT = "Source changes stay local until a compile or export step materializes release-ready payloads."
_DEFAULT_PROMPT_EFFECT = "Prompt-visible changes apply only after a compile or export uses the saved source package."
_DEFAULT_CORPUS_EFFECT = "Corpus-visible changes appear only after export and activation."


def build_response(
    action: str,
    *,
    allowed_values: Iterable[object] = (),
    required_fields: Iterable[object] = (),
    references_existing_codes: Iterable[object] = (),
    compile_effect: str = _DEFAULT_COMPILE_EFFECT,
    validation_risks: Iterable[object] = (),
    corpus_effect: str = _DEFAULT_CORPUS_EFFECT,
    prompt_effect: str = _DEFAULT_PROMPT_EFFECT,
    **extra: object,
) -> dict[str, object]:
    return {
        "status": "ok",
        "action": action,
        "allowed_values": [str(item) for item in allowed_values if str(item).strip()],
        "required_fields": [str(item) for item in required_fields if str(item).strip()],
        "references_existing_codes": [str(item) for item in references_existing_codes if str(item).strip()],
        "used_by_modules": list(_USED_BY_MODULES),
        "compile_effect": str(compile_effect or ""),
        "validation_risks": [str(item) for item in validation_risks if str(item).strip()],
        "corpus_effect": str(corpus_effect or ""),
        "prompt_effect": str(prompt_effect or ""),
        **extra,
    }
