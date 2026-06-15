"""Path-stable facade for source-authoring operations."""
from __future__ import annotations

from typing import Any

from ..semantic_release import publish_semantic_release
from ..taxonomy_compile import ensure_compiled_taxonomy_assets
from . import corpus_proxy
from .kernel_release_domain import dispatch_kernel_owner_action
from .minimal_custom_release import create_minimal_custom_release
from .operation_activation import activate_semantic_release, create_and_activate_new_corpus_db
from .operation_blueprints import derive_working_release_from_blueprint, list_default_blueprints
from .operation_build_chain import compile_release_package, export_semantic_release, validate_release_package
from .operation_review_apply import bootstrap_release_package, preview_impact, refine_release_package
from .review_bootstrap import review_bootstrap_release
from .review_data_informed import review_data_informed_release


def dispatch(action: str, payload: dict[str, Any], *, project_root) -> dict[str, object]:
    actions = {
        "list_default_blueprints": lambda: list_default_blueprints(project_root),
        "materialize_custom_taxonomy_artifact": lambda: dispatch_kernel_owner_action(action, payload, project_root=project_root),
        "materialize_custom_projection_artifact": lambda: dispatch_kernel_owner_action(action, payload, project_root=project_root),
        "apply_taxonomy_update_state": lambda: dispatch_kernel_owner_action(action, payload, project_root=project_root),
        "apply_projection_update_state": lambda: dispatch_kernel_owner_action(action, payload, project_root=project_root),
        "remove_taxonomy_from_release": lambda: dispatch_kernel_owner_action(action, payload, project_root=project_root),
        "remove_projection_from_release": lambda: dispatch_kernel_owner_action(action, payload, project_root=project_root),
        "validate_projection_binding": lambda: dispatch_kernel_owner_action(action, payload, project_root=project_root),
        "compile_semantic_release_candidate": lambda: dispatch_kernel_owner_action(action, payload, project_root=project_root),
        "materialize_semantic_release_candidate": lambda: dispatch_kernel_owner_action(action, payload, project_root=project_root),
        "merge_semantic_release_candidates": lambda: dispatch_kernel_owner_action(action, payload, project_root=project_root),
        "derive_working_release_from_blueprint": lambda: derive_working_release_from_blueprint(project_root, payload),
        "create_minimal_custom_release": lambda: create_minimal_custom_release(project_root, payload),
        "preview_impact": lambda: preview_impact(project_root),
        "review_bootstrap_release": lambda: review_bootstrap_release(project_root, payload),
        "bootstrap_release_package": lambda: bootstrap_release_package(project_root, payload),
        "review_data_informed_release": lambda: review_data_informed_release(project_root, payload),
        "refine_release_package": lambda: refine_release_package(project_root, payload),
        "validate_release_package": lambda: validate_release_package(project_root, payload),
        "compile_release_package": lambda: compile_release_package(project_root, payload),
        "export_semantic_release": lambda: export_semantic_release(project_root, payload),
        "activate_semantic_release": lambda: activate_semantic_release(project_root, payload),
        "create_and_activate_new_corpus_db": lambda: create_and_activate_new_corpus_db(project_root, payload),
    }
    try:
        return actions[action]()
    except KeyError as exc:
        raise ValueError(f"Unbekannte Source-Operation: {action}") from exc


__all__ = [
    "activate_semantic_release",
    "bootstrap_release_package",
    "compile_release_package",
    "create_and_activate_new_corpus_db",
    "dispatch_kernel_owner_action",
    "create_minimal_custom_release",
    "corpus_proxy",
    "derive_working_release_from_blueprint",
    "dispatch",
    "export_semantic_release",
    "ensure_compiled_taxonomy_assets",
    "list_default_blueprints",
    "preview_impact",
    "publish_semantic_release",
    "refine_release_package",
    "review_bootstrap_release",
    "review_data_informed_release",
    "validate_release_package",
]
