from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from phase12_merge_entry_results import missing_merge, ok_result

class FakeMergeAdapter:
    def __init__(
        self,
        *,
        missing: bool = False,
        semantic_collision: bool = False,
        forged_resolved_semantic_collision: bool = False,
        missing_materialization: bool = False,
        backfill_required: bool = False,
    ) -> None:
        self.missing = missing
        self.semantic_collision = semantic_collision
        self.forged_resolved_semantic_collision = forged_resolved_semantic_collision
        self.missing_materialization = missing_materialization
        self.backfill_required = backfill_required
        self.calls: list[str] = []
        self.request_payloads: dict[str, list[dict[str, Any]]] = {}

    def multi_source_merge_preflight(self, request_payload: Mapping[str, Any] | None = None):
        self.calls.append("multi_source_merge_preflight")
        if self.missing:
            return missing_merge("database_merge_additive_only")
        return ok_result("database_merge_additive_only", {"preflight_status": "ok"})

    def merge_empty_databases(self, request_payload: Mapping[str, Any] | None = None):
        self.calls.append("merge_empty_databases")
        self.request_payloads.setdefault("merge_empty_databases", []).append(dict(request_payload or {}))
        return ok_result("merge_database_empty", {"empty_merge_proof": True})

    def merge_filled_databases(self, request_payload: Mapping[str, Any] | None = None):
        self.calls.append("merge_filled_databases")
        self.request_payloads.setdefault("merge_filled_databases", []).append(dict(request_payload or {}))
        selection = request_payload["selection"]
        mappings = []
        for index, src in enumerate(selection["source_databases"], start=1):
            if src.get("source_state") == "empty":
                continue
            missing = self.missing_materialization and index == 1
            mappings.append(
                {
                    "pipeline_batch_collision": index > 1,
                    "projection_fingerprint": "" if missing else f"sha256:projection{index}",
                    "projection_id": "" if missing else "projection.default",
                    "release_fingerprint": "" if missing else src["source_release_fingerprint"],
                    "semantic_release_id": "" if missing else src["source_semantic_release_id"],
                    "semantic_release_version": "" if missing else src["source_semantic_release_version"],
                    "source_artifact_path": "Documents/originals/source.pdf",
                    "source_content_hash": f"sha256:content{index}",
                    "source_database_id": src["source_database_id"],
                    "source_database_path": src["source_database_path"],
                    "source_document_id": f"doc_{index}",
                    "source_embedding_id": f"emb_{index}",
                    "source_original_file_name": "source.pdf",
                    "source_pipeline_batch_id": "batch_shared",
                    "source_record_id": f"rec_{index}",
                    "target_artifact_path": f"Documents/originals/{src['source_database_id']}/source.pdf",
                    "target_document_id": f"target_doc_{index}",
                    "target_embedding_id": f"target_emb_{index}",
                    "target_pipeline_batch_id": "",
                    "target_record_id": f"target_rec_{index}",
                    "taxonomy_fingerprint": "" if missing else f"sha256:taxonomy{index}",
                }
            )
        id_map_path = (
            Path(str(selection["target_artifact_root"]))
            / "Documents"
            / "logs"
            / "merge_runs"
            / str(selection["merge_run_id"])
            / "merge_id_map.json"
        )
        id_map_path.parent.mkdir(parents=True, exist_ok=True)
        id_map_path.write_text(json.dumps({"mappings": mappings}, sort_keys=True), encoding="utf-8")
        return ok_result(
            "merge_database_filled_additive",
            {
                "artifact_copy_report": {"copied_artifact_count": len(mappings)},
                "backfill_required": self.backfill_required,
                "merge_id_map_ref": {"artifact_path": id_map_path.relative_to(Path(str(selection["target_artifact_root"]))).as_posix()},
            },
        )

    def merge_semantic_release_candidates(self, request_payload: Mapping[str, Any] | None = None):
        self.calls.append("merge_semantic_release_candidates")
        self.request_payloads.setdefault("merge_semantic_release_candidates", []).append(dict(request_payload or {}))
        collisions = []
        if self.semantic_collision:
            from semantic_control_kernel.workflows.merge.collision_manifest import build_collision_entry

            collisions.append(
                build_collision_entry(
                    collision_id="col_semantic_001",
                    collision_class="taxonomy_code_different_meaning",
                    source_refs=[{"source_database_id": "source_db_a"}, {"source_database_id": "source_db_b"}],
                )
            )
        if self.forged_resolved_semantic_collision:
            collisions.append(
                {
                    "blocks_activation": False,
                    "collision_class": "taxonomy_code_different_meaning",
                    "collision_id": "col_owner_forged",
                    "default_policy": "requires_reconcile",
                    "diagnostics": [{"owner_claim": "already resolved"}],
                    "requires_user_choice": False,
                    "resolution_owner": "owner_adapter",
                    "resolution_status": "resolved",
                    "selected_resolution": None,
                    "source_refs": [{"source_database_id": "source_db_a"}, {"source_database_id": "source_db_b"}],
                    "target_ref": {},
                }
            )
        return ok_result(
            "merge_taxonomy_and_projections_additive",
            {
                "collisions": collisions,
                "reconciled_projection_refs": [
                    {
                        "projection_fingerprint": "sha256:projection_merged",
                        "projection_id": "projection.default",
                    }
                ],
                "reconciled_taxonomy_ref": {
                    "runtime_locale": "en",
                    "taxonomy_fingerprint": "sha256:taxonomy_merged",
                    "taxonomy_id": "taxonomy.merged",
                },
                "semantic_merge_package": {"release_id": "merged.release", "runtime_locale": "en"},
            },
        )

    def write_merge_reconciliation_manifest(self, request_payload: Mapping[str, Any] | None = None):
        self.calls.append("write_merge_reconciliation_manifest")
        self.request_payloads.setdefault("write_merge_reconciliation_manifest", []).append(dict(request_payload or {}))
        return ok_result("reconcile_merged_database", {"manifest_written": True})

    def write_combined_database(self, request_payload: Mapping[str, Any] | None = None):
        self.calls.append("write_combined_database")
        return ok_result("write_combined_database", {"database_written": True})

    def fill_artifact_tree(self, request_payload: Mapping[str, Any] | None = None):
        self.calls.append("fill_artifact_tree")
        return ok_result("fill_artifact_folder_tree", {"artifact_path_mappings": []})
