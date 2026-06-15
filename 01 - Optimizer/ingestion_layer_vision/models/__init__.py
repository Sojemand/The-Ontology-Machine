"""Stable models surface for the Optimizer."""
from __future__ import annotations

from . import repository as _repository
from .document_types import (
    BlockFormatting,
    BlockPosition,
    BlockType,
    ContextInfo,
    DataBlock,
    ExtractionInfo,
    FileFormat,
    RawExtract,
    SourceInfo,
    StructuralSignature,
    ValueType,
)
from .plugin_types import ExtractResult, PluginManifest, PluginRegistryEntry
from .raw_workflow import RAW_SCHEMA_VERSION, raw_extract_to_dict, write_raw_extract
from .repository import (
    _ATOMIC_WRITE_LOCKS,
    _ATOMIC_WRITE_LOCKS_GUARD,
    _atomic_write_lock,
    _replace_with_retry,
    atomic_json_write,
    atomic_text_write,
)
from .runtime_types import (
    FileTooLargeError,
    IngestionConfig,
    IngestionReport,
    IngestorError,
    InputFileNotFoundError,
    OutputFilters,
    PluginError,
    UnsupportedFormatError,
    human_size,
)

json = _repository.json
os = _repository.os
time = _repository.time


def load_config(config_path):
    from .config import load_config as _load_config

    return _load_config(config_path)


__all__ = [
    "RAW_SCHEMA_VERSION",
    "BlockFormatting",
    "BlockPosition",
    "BlockType",
    "ContextInfo",
    "DataBlock",
    "ExtractResult",
    "ExtractionInfo",
    "FileFormat",
    "FileTooLargeError",
    "IngestionConfig",
    "IngestionReport",
    "IngestorError",
    "InputFileNotFoundError",
    "OutputFilters",
    "PluginError",
    "PluginManifest",
    "PluginRegistryEntry",
    "RawExtract",
    "SourceInfo",
    "StructuralSignature",
    "UnsupportedFormatError",
    "ValueType",
    "_ATOMIC_WRITE_LOCKS",
    "_ATOMIC_WRITE_LOCKS_GUARD",
    "_atomic_write_lock",
    "_replace_with_retry",
    "atomic_json_write",
    "atomic_text_write",
    "human_size",
    "json",
    "load_config",
    "os",
    "raw_extract_to_dict",
    "time",
    "write_raw_extract",
]

