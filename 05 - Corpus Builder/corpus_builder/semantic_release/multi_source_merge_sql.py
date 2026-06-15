from __future__ import annotations

from typing import Any, Mapping

from .multi_source_merge_sql_copy import merge_sql_databases
from .multi_source_merge_sql_map import build_id_map_mappings


def id_map_mappings(selection: Mapping[str, Any]) -> list[dict[str, Any]]:
    return build_id_map_mappings(selection)


__all__ = ["id_map_mappings", "merge_sql_databases"]
