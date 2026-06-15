"""Named schema contract carriers for the Corpus Builder database."""

from __future__ import annotations

from dataclasses import dataclass

CORPUS_SCHEMA_VERSION = "10"
DEPRECATED_TABLES = ("document_slot_candidates", "document_slots")
_CONSTRAINT_PREFIXES = ("PRIMARY KEY", "FOREIGN KEY", "UNIQUE", "CHECK", "CONSTRAINT")


@dataclass(frozen=True, slots=True)
class TableContract:
    name: str
    ddl: str
    debug_hint: str


@dataclass(frozen=True, slots=True)
class IndexContract:
    sql: str


def ddl_column_names(ddl: str) -> tuple[str, ...]:
    columns: list[str] = []
    for raw_line in ddl.strip().splitlines()[1:]:
        line = raw_line.strip().rstrip(",")
        if not line or line == ");":
            continue
        if line.upper().startswith(_CONSTRAINT_PREFIXES):
            continue
        columns.append(line.split()[0])
    return tuple(columns)
