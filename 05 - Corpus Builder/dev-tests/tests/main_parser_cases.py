"""CLI parser compatibility cases for Corpus Builder Vision."""

from __future__ import annotations

import pytest

from corpus_builder.main import build_parser


@pytest.mark.parametrize("flag", ["--source-file", "--asset-path"])
def test_load_parser_rejects_removed_legacy_flags(flag: str) -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["load", "--input", "doc.structured.normalized.json", flag, "legacy"])
