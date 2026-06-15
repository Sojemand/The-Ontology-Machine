"""Path-stable surface for Corpus Builder database helpers."""

from __future__ import annotations

from .debug import get_schema_description
from .repository import (
    avg,
    connect,
    connect_readonly,
    count,
    find_by_file_path,
    get_fields_dict,
    get_orgs_list,
    get_people_list,
    get_relations_list,
    get_rows_list,
    get_tags_list,
    group_count,
    group_sum,
    max_col,
    min_col,
    sum_col,
    top_n,
)
from .types import CORPUS_SCHEMA_VERSION
from .workflow import ensure_schema, has_initialized_schema

__all__ = [
    "CORPUS_SCHEMA_VERSION",
    "avg",
    "connect",
    "connect_readonly",
    "count",
    "ensure_schema",
    "has_initialized_schema",
    "find_by_file_path",
    "get_fields_dict",
    "get_orgs_list",
    "get_people_list",
    "get_relations_list",
    "get_rows_list",
    "get_schema_description",
    "get_tags_list",
    "group_count",
    "group_sum",
    "max_col",
    "min_col",
    "sum_col",
    "top_n",
]
