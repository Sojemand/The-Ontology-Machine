from __future__ import annotations

from types import MappingProxyType

from semantic_control_kernel.domain.state_machine.models import ConfirmationGate, TransitionRule


SEMANTIC_RELEASE_STATES = (
    "no_semantic_release",
    "semantic_release_incomplete",
    "semantic_release_complete_not_active",
    "semantic_release_active",
    "unknown",
)


def _state_tokens(required_state_text: str) -> tuple[str, ...]:
    text = required_state_text
    tokens = [state for state in SEMANTIC_RELEASE_STATES if state in text]
    lowered = text.casefold()
    if "active_database empty" in lowered or "all empty" in lowered or "database empty" in lowered:
        tokens.append("database_empty_required")
    if (
        "active_database filled" in lowered
        or "all filled" in lowered
        or "database filled" in lowered
        or "database is filled" in lowered
    ):
        tokens.append("database_filled_required")
    if "artifact tree exists" in lowered or "artifact tree has intact" in lowered or "artifact tree target" in lowered:
        tokens.append("artifact_tree_required")
    if "no active artifact tree" in lowered:
        tokens.append("no_active_artifact_tree_required")
    if "any active_database state" in lowered:
        tokens.append("any_active_database_state")
    if "merge route internal" in lowered or "rebuild route internal" in lowered or "no direct state mutation" in lowered:
        tokens.append("internal_context")
    if "merge route target" in lowered:
        tokens.append("merge_target_context")
    if "detached" in lowered:
        tokens.append("detached_context")
    if "rebuilt database exists" in lowered:
        tokens.append("rebuilt_database_required")
    if not tokens and lowered == "any":
        tokens.append("any")
    return tuple(dict.fromkeys(tokens))


def _r(
    index: int,
    function_or_route: str,
    required_state_text: str,
    required_inputs_text: str,
    writes_or_mutates: str,
    post_state_text: str,
    blocks_if: tuple[str, ...],
    confirmation_gate: str,
    recovery_states: tuple[str, ...],
) -> TransitionRule:
    required_inputs = () if required_inputs_text in {"none", "deprecated alias candidate only"} else (required_inputs_text,)
    return TransitionRule(
        rule_id=f"tr_{index:03d}",
        function_or_route=function_or_route,
        required_state=_state_tokens(required_state_text),
        required_state_text=required_state_text,
        required_inputs=required_inputs,
        required_evidence=required_inputs,
        writes_or_mutates=writes_or_mutates,
        post_state=_post_state_value(post_state_text),
        post_state_text=post_state_text,
        blocks_if=blocks_if,
        confirmation_gate=confirmation_gate,
        default_recovery_states=recovery_states,
    )


def _post_state_value(post_state_text: str) -> str:
    for state in SEMANTIC_RELEASE_STATES:
        if state in post_state_text:
            return state
    if post_state_text.startswith("same semantic release state"):
        return "same_as_before"
    if post_state_text.startswith("unchanged"):
        return "unchanged"
    if post_state_text.startswith("detached"):
        return "detached_artifact"
    return post_state_text


TRANSITION_RULES: tuple[TransitionRule, ...] = (
    _r(1, "create_standard_artifact_folder_tree", "no active artifact tree for target path", "chosen artifact root folder, artifact root name", "Standard Artifact Tree folders", "unchanged", ("invalid_target_path", "target_conflict"), ConfirmationGate.NONE.value, ("target_identity_changed", "support_only_unrecoverable")),
    _r(2, "create_empty_database", "artifact tree exists", "database name, Corpus folder", "empty database in Corpus folder", "no_semantic_release", ("missing_artifact_tree", "target_conflict", "binding_conflict"), ConfirmationGate.NONE.value, ("broken_database_artifact_binding", "target_identity_changed")),
    _r(3, "attach_semantic_release_to_database", "no_semantic_release or semantic_release_incomplete or semantic_release_complete_not_active or semantic_release_active", "written complete semantic release object or path", "database semantic release pointer", "semantic_release_complete_not_active", ("release_missing", "release_incomplete", "release_not_written", "release_fingerprint_mismatch", "database_missing"), ConfirmationGate.NONE.value, ("semantic_release_incomplete_staged", "target_identity_changed")),
    _r(4, "attach_default_semantic_release_to_database", "no_semantic_release or semantic_release_incomplete", "written complete default_semantic_release object or path", "database semantic release pointer through attach_semantic_release_to_database", "semantic_release_complete_not_active", ("release_missing", "release_incomplete", "release_not_written", "database_missing"), ConfirmationGate.NONE.value, ("semantic_release_incomplete_staged", "target_identity_changed")),
    _r(5, "attach_custom_semantic_release_to_database", "no_semantic_release or semantic_release_incomplete", "written complete custom semantic release object or path", "database semantic release pointer through attach_semantic_release_to_database", "semantic_release_complete_not_active", ("release_missing", "release_incomplete", "release_not_written", "database_missing"), ConfirmationGate.NONE.value, ("semantic_release_incomplete_staged", "target_identity_changed")),
    _r(6, "write_semantic_release", "semantic_release_incomplete or semantic_release_complete_not_active or semantic_release_active or detached release context", "complete semantic release object or intentionally staged incomplete release artifacts", "Artifact Tree Semantic Release folder artifacts", "unchanged", ("release_missing", "missing_artifact_tree", "release_fingerprint_mismatch"), ConfirmationGate.NONE.value, ("semantic_release_incomplete_staged", "target_identity_changed")),
    _r(7, "activate_semantic_release", "semantic_release_complete_not_active", "attached complete semantic release pointer and written release artifact", "runtime-active semantic release marker / database metadata", "semantic_release_active", ("attach_pointer_missing", "release_incomplete", "release_not_written", "projection_taxonomy_invalid", "active_run_lock_conflict", "release_fingerprint_mismatch"), ConfirmationGate.NONE.value, ("semantic_release_incomplete_staged", "stale_lock", "target_identity_changed")),
    _r(8, "remove_projection_from_database", "semantic_release_complete_not_active", "attached complete default release with default projections", "taxonomy-only staged default release evidence for creation workflow", "semantic_release_incomplete", ("attach_pointer_missing", "release_missing", "projection_taxonomy_invalid", "pipeline_capability_missing"), ConfirmationGate.NONE.value, ("semantic_release_incomplete_staged", "support_only_unrecoverable")),
    _r(9, "stage_custom_taxonomy_for_semantic_release", "no_semantic_release or semantic_release_incomplete", "validated custom taxonomy or `kernel.create_taxonomy_update_state.input.v1`", "staged taxonomy in Semantic Release folder", "semantic_release_incomplete", ("update_state_invalid", "release_fingerprint_mismatch", "active_run_lock_conflict", "pipeline_capability_missing"), ConfirmationGate.NONE.value, ("final_llm_validation_failure", "semantic_release_incomplete_staged")),
    _r(10, "stage_custom_projections_for_semantic_release", "no_semantic_release or semantic_release_incomplete", "validated projections or `kernel.create_projections_update_state.input.v1`, staged or active taxonomy", "staged projections in Semantic Release folder", "semantic_release_incomplete", ("update_state_invalid", "release_missing", "projection_taxonomy_invalid", "pipeline_capability_missing"), ConfirmationGate.NONE.value, ("final_llm_validation_failure", "semantic_release_incomplete_staged")),
    _r(11, "create_custom_semantic_release", "semantic_release_incomplete or detached staging context or merge finalization context", "one staged, attached or reconciled taxonomy and at least one staged, attached or reconciled validated projection", "complete custom semantic release artifact", "detached artifact produced; active_database becomes semantic_release_complete_not_active only after write_semantic_release and attach_custom_semantic_release_to_database", ("release_missing", "projection_taxonomy_invalid", "merge_collision_unresolved", "pipeline_capability_missing"), ConfirmationGate.NONE.value, ("semantic_release_incomplete_staged", "unresolved_merge_collision", "support_only_unrecoverable")),
    _r(12, "create_custom_taxonomy", "no direct state mutation", "`kernel.create_taxonomy_update_state.input.v1`", "custom taxonomy artifact", "unchanged until staged or attached through release workflow", ("update_state_invalid", "pipeline_capability_missing"), ConfirmationGate.NONE.value, ("final_llm_validation_failure", "support_only_unrecoverable")),
    _r(13, "create_custom_projection", "no direct state mutation", "`kernel.create_projections_update_state.input.v1`, valid taxonomy ref", "custom projection artifacts", "unchanged until staged or attached through release workflow", ("update_state_invalid", "projection_taxonomy_invalid", "pipeline_capability_missing"), ConfirmationGate.NONE.value, ("final_llm_validation_failure", "support_only_unrecoverable")),
    _r(14, "validate_projections_against_taxonomy", "semantic_release_incomplete or semantic_release_complete_not_active or semantic_release_active", "taxonomy and one or more projections", "validation result or blocker", "unchanged", ("projection_taxonomy_invalid",), ConfirmationGate.NONE.value, ("semantic_release_incomplete_staged", "final_llm_validation_failure")),
    _r(15, "pipeline_run", "semantic_release_active", "input files present in active artifact tree Input folder", "database records with semantic materialization refs, Documents artifacts, `kernel.pipeline_batch_manifest.v1`", "semantic_release_active", ("release_missing", "release_incomplete", "confirmation_missing", "input_missing", "materialization_provenance_missing", "active_run_lock_conflict"), ConfirmationGate.INPUT_PRESENCE_CONFIRMATION.value, ("semantic_release_incomplete_staged", "missing_manifest_or_originals", "partial_pipeline_run", "stale_lock")),
    _r(16, "reset_database", "any active_database state", "active database, artifact tree, semantic release preservation policy", "clears SQL/database content while preserving artifact tree and semantic release", "same semantic release state as before reset", ("database_missing", "release_fingerprint_mismatch", "binding_conflict"), ConfirmationGate.DESTRUCTIVE.value, ("target_identity_changed", "broken_database_artifact_binding")),
    _r(17, "empty_databases_merge_path", "selected source databases are all empty", "selected databases, selected or new artifact root, semantic releases, merge collision policy", "target artifact tree, empty target database, additive semantic release merge, merge collision manifest, reconciled semantic release", "semantic_release_active", ("database_emptiness_unknown", "release_missing", "merge_collision_unresolved", "binding_conflict"), ConfirmationGate.DESTRUCTIVE.value, ("unresolved_merge_collision", "broken_database_artifact_binding")),
    _r(18, "filled_databases_merge_path", "at least one selected source database is filled; empty sources may be present", "selected databases, artifact trees for filled contributors, semantic releases, merge collision policy", "target artifact tree, merged database content with preserved materialization refs, merge id map, merge collision manifest, reconciled SQL/artifacts/semantic release", "semantic_release_active", ("database_emptiness_unknown", "missing_artifact_tree", "merge_collision_unresolved", "materialization_provenance_missing", "merge_policy_missing"), ConfirmationGate.DESTRUCTIVE.value, ("unresolved_merge_collision", "broken_database_artifact_binding")),
    _r(19, "merge_database_empty", "merge route internal", "all source databases empty", "empty database merge result", "unchanged until route writes target", ("database_not_empty",), ConfirmationGate.NONE.value, ("unresolved_merge_collision",)),
    _r(20, "merge_database_filled_additive", "merge route internal", "at least one filled source, merge collision policy", "additive database merge result, merge id map, database collision manifest; empty sources contribute no SQL/artifact rows", "target SQL/artifacts written, release activation still pending", ("database_empty", "database_emptiness_unknown", "merge_collision_unresolved", "merge_policy_missing"), ConfirmationGate.NONE.value, ("unresolved_merge_collision",)),
    _r(21, "merge_taxonomy_and_projections_additive", "merge route internal", "source semantic releases, merge collision policy", "additive taxonomy/projection merge package, semantic collision manifest", "unchanged until semantic release is created or updated", ("release_missing", "projection_taxonomy_invalid", "merge_collision_unresolved"), ConfirmationGate.NONE.value, ("unresolved_merge_collision", "semantic_release_incomplete_staged")),
    _r(22, "reconcile_merged_semantic_release", "merge route target not yet active", "additive semantic release merge result, semantic collision manifest", "reconciled taxonomy/projection merge package, resolved semantic collision manifest", "unchanged until create_custom_semantic_release, write and attach", ("merge_collision_unresolved",), ConfirmationGate.DESTRUCTIVE.value, ("unresolved_merge_collision",)),
    _r(23, "reconcile_merged_database", "merge route target not yet active", "merged SQL data, merged artifact tree, merged semantic release, merge id map, database/artifact/semantic collision manifests", "reconciled SQL/artifacts/taxonomy/projection merge package, resolved merge collision manifest", "unchanged until create_custom_semantic_release, write and attach", ("merge_collision_unresolved", "materialization_provenance_missing"), ConfirmationGate.DESTRUCTIVE.value, ("unresolved_merge_collision", "partial_pipeline_run")),
    _r(24, "write_combined_database", "no direct state mutation", "compatibility label only", "no separate second owner mutation; SQL is written by merge_database_filled_additive", "unchanged", tuple(), ConfirmationGate.NONE.value, ("unresolved_merge_collision", "partial_pipeline_run")),
    _r(25, "fill_artifact_folder_tree", "no direct state mutation", "compatibility label only", "no separate owner call; artifacts are copied by merge_database_filled_additive", "unchanged", tuple(), ConfirmationGate.NONE.value, ("unresolved_merge_collision", "broken_database_artifact_binding")),
    _r(26, "backfill_sql", "merge or rebuild route internal", "artifact data and target database", "missing SQL records or links where recoverable", "unchanged", ("missing_artifact_tree", "database_missing", "materialization_provenance_missing"), ConfirmationGate.NONE.value, ("partial_pipeline_run", "broken_database_artifact_binding")),
    _r(27, "corpus_builder_load_semantic_release", "rebuild route internal", "Artifact Tree Semantic Release folder", "loaded semantic release for Corpus Builder", "unchanged", ("release_missing", "release_incomplete", "projection_taxonomy_invalid"), ConfirmationGate.NONE.value, ("semantic_release_incomplete_staged",)),
    _r(28, "run_corpus_builder", "rebuild route internal", "loaded semantic release, artifact tree data, target database path", "rebuilt database", "semantic_release_complete_not_active", ("release_incomplete", "invalid_target_path", "missing_artifact_tree"), ConfirmationGate.NONE.value, ("semantic_release_incomplete_staged", "broken_database_artifact_binding")),
    _r(29, "create_embeddings", "rebuilt database exists", "embedding API configured, database records", "embedding records/indexes", "unchanged", ("embedding_unavailable",), ConfirmationGate.NONE.value, ("support_only_unrecoverable",)),
    _r(30, "database_rebuild_from_artifacts", "selected Artifact Tree has intact semantic release", "artifact tree, target database name, optional overwrite confirmation", "rebuilt database, optional embeddings, activation", "semantic_release_active", ("release_missing", "release_incomplete", "target_conflict", "confirmation_missing", "database_missing"), ConfirmationGate.OVERWRITE_ONLY.value, ("semantic_release_incomplete_staged", "target_identity_changed", "broken_database_artifact_binding")),
)

TRANSITION_RULE_BY_FUNCTION = MappingProxyType({rule.function_or_route: rule for rule in TRANSITION_RULES})


def get_transition_rule(function_or_route: str) -> TransitionRule:
    try:
        return TRANSITION_RULE_BY_FUNCTION[function_or_route]
    except KeyError as exc:
        raise ValueError(f"Unknown transition function or route: {function_or_route}") from exc


def parse_spec_02_transition_rows(markdown_text: str) -> tuple[dict[str, str], ...]:
    rows: list[dict[str, str]] = []
    in_table = False
    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if line.startswith("Recovery State Classes"):
            break
        if line.startswith("| Function / Route "):
            in_table = True
            continue
        if not in_table or not line.startswith("|"):
            continue
        if line.startswith("|---"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 7:
            continue
        rows.append(
            {
                "function_or_route": cells[0],
                "required_state_text": cells[1],
                "required_inputs_text": cells[2],
                "writes_or_mutates": cells[3],
                "post_state_text": cells[4],
                "blocks_if_text": cells[5],
                "confirmation_text": cells[6],
            }
        )
    return tuple(rows)
