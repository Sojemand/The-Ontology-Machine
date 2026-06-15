"""Report persistence for the processor repository surface."""
from __future__ import annotations

import sys
from dataclasses import asdict


def write_report(processor) -> None:
    data = asdict(processor._report)
    data.pop("current_file", None)
    data.pop("current_plugin", None)
    _processor_surface().atomic_json_write(processor._output_dir / "ingestion_report.json", data)


def _processor_surface():
    return sys.modules[__package__]
