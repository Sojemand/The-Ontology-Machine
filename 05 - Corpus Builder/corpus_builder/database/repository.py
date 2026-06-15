"""Path-stable re-export surface for corpus.db repository helpers."""

from __future__ import annotations

from .repository_connection import connect, connect_readonly
from .repository_documents import (
    clear_all_embeddings,
    find_by_file_path,
    get_fields_dict,
    get_orgs_list,
    get_people_list,
    get_relations_list,
    get_rows_list,
    get_tags_list,
    list_archived_documents,
)
from .repository_queries import avg, count, group_count, group_sum, max_col, min_col, sum_col, top_n

__all__ = [
    "avg",
    "clear_all_embeddings",
    "connect",
    "connect_readonly",
    "count",
    "find_by_file_path",
    "get_fields_dict",
    "get_orgs_list",
    "get_people_list",
    "get_relations_list",
    "get_rows_list",
    "get_tags_list",
    "group_count",
    "group_sum",
    "list_archived_documents",
    "max_col",
    "min_col",
    "sum_col",
    "top_n",
]
