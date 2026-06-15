from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.paths import path_hash

from phase12_merge_entry_fixtures import create_artifact_tree
from phase12_merge_entry_results import ok_result

class FakeWorkspaceAdapter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def prepare_artifact_tree(self, request_payload: Mapping[str, Any] | None = None):
        self.calls.append("prepare_artifact_tree")
        create_artifact_tree(Path(request_payload["selection"]["target_artifact_root"]))
        return ok_result("create_standard_artifact_folder_tree", {"artifact_root": request_payload["selection"]["target_artifact_root"]})


class FakeCorpusAdapter:
    def __init__(self, *, insufficient_rebuild: bool = False, omit_release_identity: bool = False) -> None:
        self.insufficient_rebuild = insufficient_rebuild
        self.omit_release_identity = omit_release_identity
        self.calls: list[str] = []

    def create_empty_database(self, request_payload: Mapping[str, Any] | None = None):
        self.calls.append("create_empty_database")
        db = Path(str(request_payload["database_path"]))
        db.parent.mkdir(parents=True, exist_ok=True)
        db.write_text("", encoding="utf-8")
        return ok_result("create_empty_database", {"database_path": str(db), "database_path_hash": path_hash(db)})

    def rebuild_from_artifacts(self, request_payload: Mapping[str, Any] | None = None):
        self.calls.append("rebuild_from_artifacts")
        db = Path(str(request_payload["corpus_db_path"]))
        db.parent.mkdir(parents=True, exist_ok=True)
        db.write_text("rebuilt", encoding="utf-8")
        output_path = str(db.parent / "wrong.db") if self.insufficient_rebuild else str(db)
        output_refs = {
            "database_path": output_path,
            "record_count": 2,
        }
        if not self.omit_release_identity:
            output_refs["loaded_release_fingerprint"] = request_payload["loaded_semantic_release"]["loaded_release_fingerprint"]
        return ok_result("run_corpus_builder", output_refs)

    def backfill_sql(self, request_payload: Mapping[str, Any] | None = None):
        self.calls.append("backfill_sql")
        return ok_result("backfill_sql", {"backfilled": True})
