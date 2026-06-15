from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


DRIFT_PREFLIGHT = MappingProxyType(
    {
        "status": "drift_preflight: build_plan_authority_applied",
        "items": (
            {
                "document": "03_database_provenance_and_merge_policy.md",
                "detail": "pipeline_batch_id_collision allows source database ID or import mapping.",
                "applied_authority": "Phase 12 requires target pipeline_batch_id to use the unique source batch ID or <source_database_id>.<source_pipeline_batch_id>.",
            },
            {
                "document": "10_kernel_only_functions.md",
                "detail": "mentions deprecated merge_taxonomy_projections_sql_data_additive and merge_database_filled aliases.",
                "applied_authority": "Phase 12 implements only merge_database_filled_additive and blocks old alias/public route revival.",
            },
        ),
    }
)


@dataclass(frozen=True)
class MergeCollisionPolicy:
    collision_class: str
    default_policy: str
    user_decision: bool
    owner_function: str
    blocks_if: str

    def to_dict(self) -> dict[str, object]:
        return {
            "blocks_if": self.blocks_if,
            "collision_class": self.collision_class,
            "default_policy": self.default_policy,
            "owner_function": self.owner_function,
            "user_decision": self.user_decision,
        }


def _p(
    collision_class: str,
    default_policy: str,
    user_decision: bool,
    owner_function: str,
    blocks_if: str,
) -> MergeCollisionPolicy:
    return MergeCollisionPolicy(
        collision_class=collision_class,
        default_policy=default_policy,
        user_decision=user_decision,
        owner_function=owner_function,
        blocks_if=blocks_if,
    )


COLLISION_POLICIES: tuple[MergeCollisionPolicy, ...] = (
    _p("taxonomy_code_same_fingerprint", "merge one canonical code", False, "merge_taxonomy_and_projections_additive", "fingerprint cannot be verified"),
    _p("taxonomy_code_different_meaning", "requires_reconcile", True, "reconcile_merged_semantic_release or reconcile_merged_database", "rename, merge or mapping decision missing"),
    _p("taxonomy_code_same_label_different_code", "keep both unless user maps", True, "reconcile_merged_semantic_release or reconcile_merged_database", "relationship ambiguity remains"),
    _p("projection_id_same_fingerprint", "merge one canonical projection", False, "merge_taxonomy_and_projections_additive", "fingerprint cannot be verified"),
    _p("projection_id_different_fingerprint", "requires_reconcile", True, "reconcile_merged_semantic_release or reconcile_merged_database", "rename, merge or mapping decision missing"),
    _p("projection_include_conflict", "requires_reconcile", True, "reconcile_merged_semantic_release or reconcile_merged_database", "included taxonomy codes unresolved"),
    _p("document_content_hash_duplicate", "keep both by default", False, "reconcile_merged_database", "selected collapse cannot preserve all source refs"),
    _p("same_original_hash_different_file_name", "keep one content identity with aliases", True, "reconcile_merged_database", "collapse changes record count without receipt"),
    _p("same_file_name_different_hash", "rename with source database prefix", False, "merge_database_filled_additive", "unique target path cannot be produced"),
    _p("document_id_collision", "remap target document IDs", False, "merge_database_filled_additive", "ID map cannot preserve source and target IDs"),
    _p("sql_primary_key_collision", "remap target SQL IDs", False, "merge_database_filled_additive", "FK graph cannot be rewired"),
    _p("artifact_path_collision", "rename with source DB prefix and record suffix", False, "merge_database_filled_additive", "renamed path still collides or source artifact missing"),
    _p("pipeline_batch_id_collision", "namespace with source database ID", False, "merge_database_filled_additive", "batch provenance cannot be preserved"),
    _p("embedding_id_collision", "remap vector/embedding IDs", False, "merge_database_filled_additive or create_embeddings", "embedding cannot be linked to remapped target record"),
    _p("same_embedding_source_hash_different_embedding_model", "keep separate embedding records by model/config fingerprint", False, "merge_database_filled_additive or create_embeddings", "embedding config fingerprint missing"),
    _p("record_release_version_mixed", "preserve original materialization refs", False, "merge_database_filled_additive", "old release refs cannot be queried after merge"),
)

COLLISION_POLICY_BY_CLASS: Mapping[str, MergeCollisionPolicy] = MappingProxyType(
    {policy.collision_class: policy for policy in COLLISION_POLICIES}
)


def collision_policy(collision_class: str) -> MergeCollisionPolicy:
    try:
        return COLLISION_POLICY_BY_CLASS[collision_class]
    except KeyError as exc:
        raise ValueError(f"Unknown Phase 12 collision class: {collision_class}") from exc


def collision_requires_user_choice(collision_class: str, *, selected_resolution: str | None = None) -> bool:
    policy = collision_policy(collision_class)
    if collision_class == "document_content_hash_duplicate":
        return selected_resolution == "collapse"
    if collision_class == "taxonomy_code_same_label_different_code":
        return selected_resolution == "map"
    return policy.user_decision


def collision_blocks_activation(collision: Mapping[str, object]) -> bool:
    status = collision.get("resolution_status")
    if status in {"unresolved", "requires_user_choice"}:
        return True
    return bool(collision.get("blocks_activation"))


def activation_blocking_collisions(collisions: list[Mapping[str, object]]) -> list[Mapping[str, object]]:
    return [collision for collision in collisions if collision_blocks_activation(collision)]
