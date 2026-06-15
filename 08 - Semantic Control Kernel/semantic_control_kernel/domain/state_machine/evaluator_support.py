from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping

from semantic_control_kernel.domain.state_machine.blockers import make_state_blocker
from semantic_control_kernel.domain.state_machine.models import StateBlocker, TransitionInputRefs, TransitionRule
from semantic_control_kernel.types.enums import DatabaseEmptiness, SemanticReleaseState
from semantic_control_kernel.types.state import ActiveDatabaseState

BlockerFactory = Callable[[str, str, str, str, Mapping[str, Any]], StateBlocker]


def state_payload(active_state: ActiveDatabaseState | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(active_state, ActiveDatabaseState):
        return active_state.to_dict()
    if hasattr(active_state, "payload") and isinstance(getattr(active_state, "payload"), Mapping):
        return deepcopy(dict(getattr(active_state, "payload")))
    return deepcopy(dict(active_state))


def snapshot_id(state: Mapping[str, Any]) -> str:
    return str(state.get("state_snapshot_id", "state_snapshot_unknown"))


def target_identity(state: Mapping[str, Any]) -> dict[str, Any]:
    active_database = state.get("active_database", {})
    if isinstance(active_database, Mapping) and isinstance(active_database.get("target_identity"), Mapping):
        return deepcopy(dict(active_database["target_identity"]))
    artifact_tree = state.get("artifact_tree", {})
    if isinstance(artifact_tree, Mapping) and isinstance(artifact_tree.get("target_identity"), Mapping):
        return deepcopy(dict(artifact_tree["target_identity"]))
    return {}


def actual_state_text(state: Mapping[str, Any]) -> str:
    return f"{state.get('semantic_release_state', 'unknown')}:{state.get('database_emptiness', 'unknown')}"


def required_state_blocker(
    rule: TransitionRule,
    state: Mapping[str, Any],
    refs: TransitionInputRefs,
    make_blocker: BlockerFactory,
) -> StateBlocker | None:
    semantic_state = str(state.get("semantic_release_state", SemanticReleaseState.UNKNOWN.value))
    emptiness = str(state.get("database_emptiness", DatabaseEmptiness.UNKNOWN.value))
    active_database = state.get("active_database", {})
    artifact_tree = state.get("artifact_tree", {})
    database_exists = bool(isinstance(active_database, Mapping) and active_database.get("database_exists", False))
    artifact_tree_exists = bool(isinstance(artifact_tree, Mapping) and artifact_tree.get("exists", False))
    tokens = set(rule.required_state)

    if "no_active_artifact_tree_required" in tokens and artifact_tree_exists:
        return make_blocker("target_conflict", rule.function_or_route, rule.required_state_text, "artifact tree exists", state)
    if "artifact_tree_required" in tokens and not artifact_tree_exists:
        return make_blocker("missing_artifact_tree", rule.function_or_route, rule.required_state_text, "artifact tree missing", state)
    if "any_active_database_state" in tokens and not database_exists:
        return make_blocker("database_missing", rule.function_or_route, rule.required_state_text, "database missing", state)
    if "rebuilt_database_required" in tokens and not database_exists:
        return make_blocker("database_missing", rule.function_or_route, rule.required_state_text, "rebuilt database missing", state)
    if "database_empty_required" in tokens:
        blocker = emptiness_blocker(DatabaseEmptiness.EMPTY.value, emptiness, rule.function_or_route, rule.required_state_text, state)
        if blocker is not None:
            return blocker
    if "database_filled_required" in tokens:
        blocker = emptiness_blocker(DatabaseEmptiness.FILLED.value, emptiness, rule.function_or_route, rule.required_state_text, state)
        if blocker is not None:
            return blocker
    if rule.function_or_route in {"empty_databases_merge_path", "merge_database_empty"}:
        return source_emptiness_blocker(rule, refs, DatabaseEmptiness.EMPTY.value, state, make_blocker)
    if rule.function_or_route in {"filled_databases_merge_path", "merge_database_filled_additive"}:
        return source_emptiness_blocker(rule, refs, DatabaseEmptiness.FILLED.value, state, make_blocker)
    required_semantic_states = tuple(token for token in rule.required_state if token in SemanticReleaseState.values())
    if required_semantic_states and semantic_state not in required_semantic_states:
        code = "unknown_state" if semantic_state == SemanticReleaseState.UNKNOWN.value else "missing_required_state"
        return make_blocker(code, rule.function_or_route, rule.required_state_text, semantic_state, state)
    return None


def source_emptiness_blocker(
    rule: TransitionRule,
    refs: TransitionInputRefs,
    required: str,
    state: Mapping[str, Any],
    make_blocker: BlockerFactory,
) -> StateBlocker | None:
    source_values = tuple(refs.source_database_emptiness)
    if not source_values:
        return None
    if any(value == DatabaseEmptiness.UNKNOWN.value for value in source_values):
        return make_blocker("database_emptiness_unknown", rule.function_or_route, rule.required_state_text, "unknown source database", state)
    if required == DatabaseEmptiness.FILLED.value:
        if DatabaseEmptiness.FILLED.value in source_values:
            return None
        return make_blocker("database_empty", rule.function_or_route, rule.required_state_text, ",".join(source_values), state)
    if any(value != required for value in source_values):
        code = "database_empty" if required == DatabaseEmptiness.FILLED.value else "database_not_empty"
        return make_blocker(code, rule.function_or_route, rule.required_state_text, ",".join(source_values), state)
    return None


def emptiness_blocker(
    required: str,
    actual: str,
    function_or_route: str,
    required_state_text: str,
    state: Mapping[str, Any],
) -> StateBlocker | None:
    if actual == required:
        return None
    if actual == DatabaseEmptiness.UNKNOWN.value:
        code = "database_emptiness_unknown"
    elif required == DatabaseEmptiness.EMPTY.value:
        code = "database_not_empty"
    else:
        code = "database_empty"
    return make_state_blocker(
        blocker_code=code,
        function_or_route=function_or_route,
        required_state=required_state_text,
        actual_state=actual,
        target_identity=target_identity(state),
        state_snapshot_id=snapshot_id(state),
        evidence_refs=tuple(str(item) for item in state.get("evidence_refs", ())),
    )


def confirmation_stale_reason(
    rule: TransitionRule,
    state: Mapping[str, Any],
    confirmation_ref: str | None,
    receipt: Mapping[str, Any],
) -> str | None:
    status = receipt.get("user_decision") or receipt.get("status")
    if status != "confirmed":
        return f"receipt status {status!r}"
    request_id = receipt.get("confirmation_request_id") or receipt.get("interaction_request_id")
    if confirmation_ref is not None and request_id != confirmation_ref:
        return "confirmation request mismatch"
    if receipt.get("function_or_route") not in {None, rule.function_or_route}:
        return "function mismatch"
    if receipt.get("confirmation_gate") not in {None, rule.confirmation_gate}:
        return "confirmation gate mismatch"
    snapshot_identity = receipt.get("confirmed_state_snapshot_identity") or receipt.get("state_snapshot_identity")
    if not isinstance(snapshot_identity, Mapping):
        return "state snapshot missing"
    if snapshot_identity.get("state_snapshot_id") != snapshot_id(state):
        return "state snapshot mismatch"
    target = receipt.get("confirmed_target_identity") or receipt.get("target_identity")
    if not isinstance(target, Mapping):
        return "target identity missing"
    if target != target_identity(state):
        return "target identity mismatch"
    return None


def post_state_when_allowed(rule: TransitionRule, state: Mapping[str, Any]) -> str:
    if rule.post_state in {"unchanged", "same_as_before"}:
        return str(state.get("semantic_release_state", SemanticReleaseState.UNKNOWN.value))
    return rule.post_state
