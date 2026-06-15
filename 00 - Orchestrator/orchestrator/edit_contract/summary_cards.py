"""Summary-card builders for the guided Orchestrator slot."""
from __future__ import annotations

from ..policy_store import (
    load_artifact_publication_policy,
    load_execution_policy,
    load_health_dependency_policy,
    load_route_intake_policy,
)


def build_summary_cards() -> list[dict]:
    route = load_route_intake_policy()
    execution = load_execution_policy()
    health = load_health_dependency_policy()
    artifact = load_artifact_publication_policy()
    born = route["pdf_classifications"]["born_digital"]
    scan = route["pdf_classifications"]["scan"]
    born_route = route["pdf_routing"][born]
    scan_route = route["pdf_routing"][scan]
    pipeline_profile = health["scope_profiles"].get("pipeline_run", {})
    optimizer = pipeline_profile.get("optimizer", {})
    return [
        {
            "card_id": "routing_snapshot",
            "label": "Routing Snapshot",
            "body": "Saved intake defaults for route families and PDF handoff.",
            "lines": [
                f"Enabled Routes: {_csv(route['enabled_route_families'])}",
                f"PDF Bucket: {_csv(route['suffix_groups']['pdf'])} -> {born} / {scan}",
                f"Born-Digital PDF: {born_route['route_family']} via {born_route['optimizer_module_key']} -> {born_route['interpreter_module_key']}",
                f"Scan PDF: {scan_route['route_family']} via {scan_route['optimizer_module_key']} -> {scan_route['interpreter_module_key']}",
            ],
        },
        {
            "card_id": "execution_snapshot",
            "label": "Execution Snapshot",
            "body": "Saved stage names, required modules, and downstream timeout budgets.",
            "lines": [
                f"Pipeline Stages: {_csv(execution['pipeline_stage_names'])}",
                f"Global Required Modules: {_csv(execution['global_required_modules'])}",
                f"Healthcheck / Projection Timeout: {execution['healthcheck_timeout_seconds']}s / {execution['projection_catalog_timeout_seconds']}s",
                f"Configured Module Contracts: {len(execution['modules'])}",
                f"Longest Operation Timeout: {_longest_timeout(execution['operation_timeouts_seconds'])}",
            ],
        },
        {
            "card_id": "health_profiles",
            "label": "Health Profiles",
            "body": "Saved scope-aware dependency requirements used to interpret health readiness.",
            "lines": [
                f"Configured Scopes: {_csv(tuple(health['scope_profiles']))}",
                f"Pipeline-Run Modules: {_csv(tuple(pipeline_profile))}",
                f"Optimizer File-Profile Suffix Rules: {len(optimizer)}",
                f"PDF Dependencies: {_csv(optimizer.get('.pdf', [])) or 'none'}",
                f"Fallback For Other Scopes: {_fallback_label(health['fallback_for_other_scopes'])}",
            ],
        },
        {
            "card_id": "artifact_layout",
            "label": "Artifact Layout",
            "body": "Saved publication names for pipeline state, route folders, and error bundles.",
            "lines": [
                f"State / Run Workspace: {artifact['pipeline_state_dir_name']} / {artifact['run_workspace_dir_name']}",
                f"Route Folders: {_route_folder_map(artifact['route_folder_map'])}",
                f"Error Root: {artifact['error_root_name']} (legacy: {_csv(artifact['legacy_error_root_names'])})",
                f"Artifact Subdirs: {_csv(artifact['route_artifact_subdirs'])}",
                f"Interpreter Request File: {artifact['request_file_names']['interpreter_request']}",
            ],
        },
    ]


def _csv(values) -> str:
    items = [str(value).strip() for value in values if str(value).strip()]
    return ", ".join(items) if items else "none"
def _longest_timeout(timeouts: dict[str, int]) -> str:
    highest = max(timeouts.values())
    names = [name for name, value in timeouts.items() if value == highest]
    return f"{_csv(names)} @ {highest}s"


def _fallback_label(fallback: dict) -> str:
    return "empty" if not fallback else _csv(tuple(fallback))


def _route_folder_map(route_folder_map: dict[str, str]) -> str:
    return " | ".join(f"{name}={label}" for name, label in route_folder_map.items())
