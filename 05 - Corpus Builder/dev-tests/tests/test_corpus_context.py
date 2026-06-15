from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from corpus_builder.context import ModuleContext
from corpus_builder.services.corpus_context import activate_corpus_context, create_empty_corpus_db


def _context(tmp_path: Path) -> ModuleContext:
    (tmp_path / "config").mkdir()
    (tmp_path / "state").mkdir()
    (tmp_path / "output").mkdir()
    (tmp_path / "config" / "corpus_config.json").write_text(
        json.dumps({"database": {"corpus_db": str(tmp_path / "output" / "old.db")}}),
        encoding="utf-8",
    )
    return ModuleContext(tmp_path)


def test_create_empty_corpus_db_can_activate_owner_default(tmp_path: Path) -> None:
    context = _context(tmp_path)
    target = tmp_path / "output" / "fresh.db"

    result = create_empty_corpus_db(context, corpus_db_path=target, activate_context=True)

    assert result["status"] == "ok"
    assert target.exists()
    config = json.loads((tmp_path / "config" / "corpus_config.json").read_text(encoding="utf-8"))
    assert config["database"]["corpus_db"] == str(target.resolve())


def test_activate_corpus_context_requires_existing_file_and_persists_default(tmp_path: Path) -> None:
    context = _context(tmp_path)
    target = tmp_path / "output" / "existing.db"
    conn = sqlite3.connect(target)
    conn.close()

    result = activate_corpus_context(context, corpus_db_path=target)

    assert result["status"] == "ok"
    assert result["corpus_db_path"] == str(target.resolve())
    config = json.loads((tmp_path / "config" / "corpus_config.json").read_text(encoding="utf-8"))
    assert config["database"]["corpus_db"] == str(target.resolve())
