"""Runtime and filesystem adapters for the docx-python extractor."""
from __future__ import annotations

from pathlib import Path
import sys
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import BadZipFile

_OPTIMIZER_ROOT = Path(__file__).resolve().parents[3]
if str(_OPTIMIZER_ROOT) not in sys.path:
    sys.path.insert(0, str(_OPTIMIZER_ROOT))

from .adapter_conversion import cleanup_prepared_source, prepare_source
from .ooxml_snapshot import load_ooxml_snapshot
from .python_docx_snapshot import ensure_python_docx, load_python_docx_snapshot
from .types import WordDocumentSnapshot, WordStageError


def load_document_snapshot(source: Path, config: dict[str, Any] | None = None) -> WordDocumentSnapshot:
    config_data = dict(config or {})
    try:
        return load_ooxml_snapshot(source, config_data)
    except (BadZipFile, KeyError, ET.ParseError):
        pass
    except WordStageError:
        raise
    except Exception as exc:
        raise WordStageError("adapter.load", str(exc)) from exc
    return load_python_docx_snapshot(source)


__all__ = [
    "cleanup_prepared_source",
    "ensure_python_docx",
    "load_document_snapshot",
    "prepare_source",
]
