"""Launch-request validation helpers for generic debug sessions."""

from __future__ import annotations

from pathlib import Path

from .. import policy_store
from ..pipeline import route_policy

_INTERPRETER_DEBUG_MODULES = frozenset({"interpreter"})
_MODULE_SELECTED_INPUT_MODULES = frozenset({"validator", "normalizer", "corpus_builder"})
_MODULE_SELECTED_SINGLE_SUFFIXES = {
    "validator": ".structured.json",
    "normalizer": ".structured.json",
    "corpus_builder": ".structured.normalized.json",
}


def validate_launch_request(module_key: str, mode: str, input_root: Path, source_path: str) -> None:
    if module_key in _INTERPRETER_DEBUG_MODULES and mode == "single":
        _validate_interpreter_source(module_key, source_path)
        return
    if module_key in _MODULE_SELECTED_INPUT_MODULES:
        if mode == "single":
            _validate_module_selected_single_source(module_key, source_path)
        elif input_root.exists() and input_root.is_file():
            raise ValueError(
                f"{_module_label(module_key)} expects an input folder for {mode} debug, not a file: {input_root}"
            )


def _validate_interpreter_source(module_key: str, source_path: str) -> None:
    if not source_path:
        return
    candidate = Path(source_path)
    lowered_parts = {part.lower() for part in candidate.parts}
    lowered_suffixes = [suffix.lower() for suffix in candidate.suffixes]
    is_raw_json = len(lowered_suffixes) >= 2 and lowered_suffixes[-2:] == [".raw", ".json"]
    raw_extracts_dir = policy_store.publication_name("raw_extracts").lower()
    if is_raw_json or raw_extracts_dir in lowered_parts:
        raise ValueError(_raw_source_error(module_key))
    suffix = route_policy.normalized_suffix(candidate)
    allowed_suffixes = set(route_policy.image_suffixes()) | set(route_policy.file_suffixes()) | {route_policy.pdf_suffix()}
    if suffix and suffix not in allowed_suffixes:
        raise ValueError(
            "Interpreter expects a supported original file in single debug "
            f"({', '.join(route_policy.image_suffixes())}, {', '.join(route_policy.file_suffixes())}, or {route_policy.pdf_suffix()})."
        )


def _validate_module_selected_single_source(module_key: str, source_path: str) -> None:
    if not source_path:
        return
    expected_suffix = _MODULE_SELECTED_SINGLE_SUFFIXES.get(module_key)
    if not expected_suffix:
        return
    candidate = Path(source_path)
    if candidate.name.lower().endswith(expected_suffix.lower()):
        return
    if module_key == "validator":
        raise ValueError(
            "Validator expects a *.structured.json directly from the Interpreter in single debug, "
            "not *.structured.normalized.json and not an original file before the Optimizer."
        )
    if module_key == "normalizer":
        raise ValueError(
            "Normalizer expects a *.structured.json directly from the Interpreter or Validator in single debug, "
            "not *.structured.normalized.json."
        )
    raise ValueError(
        "Corpus Builder expects a *.structured.normalized.json as canonical input in single debug."
    )


def _raw_source_error(module_key: str) -> str:
    del module_key
    target = "Interpreter"
    raw_dir = policy_store.publication_name("raw_extracts")
    return (
        f"{target} expects the original file as Source Path in single debug, not an optimizer raw "
        f"under {raw_dir}/*.raw.json. Select the source file before the Optimizer. "
        "Profile dispatch to vision/file is derived from the request context in the unified Interpreter."
    )


def _module_label(module_key: str) -> str:
    if module_key == "validator":
        return "Validator"
    if module_key == "normalizer":
        return "Normalizer"
    if module_key == "corpus_builder":
        return "Corpus Builder"
    return module_key
