"""Ordered display labels for debug-host module selection."""

from __future__ import annotations

MODULE_OPTIONS = (
    ("optimizer", "Optimizer"),
    ("interpreter", "Interpreter"),
    ("validator", "Validator"),
    ("normalizer", "Normalizer"),
    ("corpus_builder", "Corpus Builder"),
)
_KNOWN_KEYS = frozenset(key for key, _label in MODULE_OPTIONS)


def ordered_options(descriptors: dict[str, object]) -> list[tuple[str, str]]:
    extras = [
        (key, getattr(descriptor, "display_name", key))
        for key, descriptor in sorted(descriptors.items())
        if key not in _KNOWN_KEYS
    ]
    return [*MODULE_OPTIONS, *extras]


def ordered_descriptor_keys(descriptors: dict[str, object]) -> list[str]:
    return [key for key, _label in ordered_options(descriptors) if key in descriptors]


def menu_values(descriptors: dict[str, object]) -> list[str]:
    return [label for _key, label in ordered_options(descriptors)]


def key_for_value(value: object, descriptors: dict[str, object]) -> str:
    text = str(value or "").strip()
    normalized = text.casefold()
    for key, label in ordered_options(descriptors):
        if normalized in {key.casefold(), label.casefold()}:
            return key
    return text if text in descriptors else ""


def label_for_key(module_key: object, descriptors: dict[str, object]) -> str:
    key = key_for_value(module_key, descriptors)
    for known_key, label in ordered_options(descriptors):
        if known_key == key:
            return label
    return str(module_key or "").strip()
