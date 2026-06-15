"""Owner-provided summary text for the Orchestrator Edit Suite slot."""

from __future__ import annotations

from textwrap import dedent


def build_module_summary() -> str:
    return dedent(
        """
        ORCHESTRATOR POLICY HELP

        Purpose
        This slot prepares the Orchestrator's next saved policy defaults for intake routing, pipeline execution, health dependency profiling, and artifact publication. The Orchestrator remains run- and debug-owned.
        This edit_contract externalizes only non-GUI owner-local policy defaults. It does not edit GUI state, credentials, or run-control data, and it does not start pipeline actions by itself.

        How To Read This Slot
        - Summary explains the module role, policy boundaries, and the intended first-time workflow.
        - Summary also adds four snapshot cards so you can review routing, execution, health profiles, and artifact layout before editing.
        - Settings is the guided working area for the four policy surfaces that the slot owns.
        - Each policy surface uses top-level groups with typed controls for simple values and JSON sub-editors for nested policy maps.
        - Prompts/Assets is intentionally empty for this module because the slot is policy-only.
        - Operations is intentionally empty in this v1 contract because run and debug control stay outside the edit workflow.
        - Preview/Drift is the review layer for current JSON values, draft values, and diffs before save.

        Surface Guide
        - Route Intake Policy (`orchestrator.route_intake_policy`): edits `config/route_intake_policy.json` for route families, suffix groups, PDF classifications, and PDF routing.
        - Execution Policy (`orchestrator.execution_policy`): edits `config/execution_policy.json` for stage names, required modules, per-module required actions, and operation timeouts.
        - Health Dependency Policy (`orchestrator.health_dependency_policy`): edits `config/health_dependency_policy.json` for scope-aware dependency requirements.
        - Artifact Publication Policy (`orchestrator.artifact_publication_policy`): edits `config/artifact_publication_policy.json` for run-folder names, route folder names, artifact subdirectories, and publication file names.

        Policy-Only Guide
        - This slot is intentionally limited to saved orchestrator policy files.
        - The goal is to make previously implicit defaults reviewable and editable without moving run control into the Edit Suite.
        - If you are looking for live session inputs, credentials, model selection, or debug host controls, you are outside the scope of this slot.

        Route Intake Policy Guide
        - `route_families` defines the known route labels. `enabled_route_families` limits which of those routes are active for future intake decisions.
        - `suffix_groups` maps file suffixes into the route families plus the dedicated PDF bucket.
        - `pdf_classifications` names the saved PDF classes and `pdf_routing` maps each class to the shared Documents route plus the canonical optimizer/interpreter modules.
        - Changes here affect the next intake and routing decisions only after the policy file is saved.

        Execution Policy Guide
        - `pipeline_stage_names` defines the saved stage labels the orchestrator uses for pipeline sequencing and reporting.
        - `global_required_modules` lists modules that must be present for a normal pipeline run regardless of intake route.
        - `healthcheck_timeout_seconds` and `projection_catalog_timeout_seconds` set the saved timeout budgets for those orchestrator-side operations.
        - `modules` stores the per-module `display_name`, `stage_role`, and required contract actions the orchestrator expects when building a run plan.
        - `operation_timeouts_seconds` sets the saved timeout for each downstream contract action such as `extract_document`, `interpret_document`, `validate_document`, `normalize_document`, and `generate_embeddings`.

        Health Dependency Policy Guide
        - `scope_profiles` stores dependency requirements by orchestrator scope.
        - The current saved profile focuses on `pipeline_run` and maps optimizer file-profile dependencies by input suffix.
        - `fallback_for_other_scopes` is the saved escape hatch for non-pipeline scopes when a scope-specific profile is not present.
        - This policy explains required dependency names only. It does not manage credentials, warnings, auth flows, or healthcheck execution itself.

        Artifact Publication Policy Guide
        - `pipeline_state_dir_name` and `run_workspace_dir_name` define where future pipeline state and run workspaces are materialized.
        - `route_folder_map` controls the saved display folder for each route family.
        - `error_root_name` and `legacy_error_root_names` define where failed cases are published and which legacy folder names remain recognized.
        - `route_artifact_subdirs` and `publication_names` define the saved artifact layout below each route folder.
        - `request_file_names` stores the canonical OCR, Interpreter, and Normalizer request artifact names.

        What This Slot Does Not Control
        - `state/ui_state.json`, `state/runtime_settings.json`, credentials, and protocol constants remain out of scope.
        - This slot does not edit `state/credentials_state.json`, `state/model_catalog_state.json`, debug host control vocabularies, or installer/runtime manifests.
        - Run, reset, embeddings, healthcheck execution, and debug-host control remain run- and debug-owned.
        - Existing run folders and published artifacts change only after a future orchestrator run uses the saved policy files.

        Recommended First-Time Workflow
        1. Start in Summary so you understand that this slot is policy-only and not a live run-control surface.
        2. Review the snapshot cards first to decide whether your change belongs to routing, execution, health dependencies, or artifact publication.
        3. Open the matching guided policy surface and adjust only the top-level group that matches your intent.
        4. Use the JSON sub-editors only for nested policy maps such as suffix groups, module contracts, or publication names.
        5. Open Preview/Drift before every save so the next orchestrator run sees exactly the policy changes you intend.
        6. Save only when the guided editor and the preview diff both match the next-run behavior you want.
        """
    ).strip()
