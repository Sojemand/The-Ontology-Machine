from __future__ import annotations

from typing import Any

from .tool_catalog_utils import _tool


def working_release_tools() -> list[dict[str, Any]]:
    return [
        _tool(
            "read_working_release",
            "Read the workspace-local working extraction pack under artifact_folder/.vp/n. This is the dedicated wrapper for Normalizer read_release_package and does not validate, compile, export, or activate.",
            {
                "artifact_folder": {"type": "string", "description": "Workspace root that owns the working release authoring truth under .vp/n."},
            },
            required=("artifact_folder",),
        ),
        _tool(
            "list_working_release_profiles",
            "List document profiles in the workspace-local working extraction pack. This is the dedicated wrapper for Normalizer list_projections and performs no build or export step.",
            {
                "artifact_folder": {"type": "string", "description": "Workspace root that owns the working release authoring truth under .vp/n."},
            },
            required=("artifact_folder",),
        ),
        _tool(
            "read_working_release_profile",
            "Read one document profile from the workspace-local working extraction pack. This is the dedicated wrapper for Normalizer read_projection.",
            {
                "artifact_folder": {"type": "string", "description": "Workspace root that owns the working release authoring truth under .vp/n."},
                "projection_id": {"type": "string", "description": "Stable profile/projection id to read."},
            },
            required=("artifact_folder", "projection_id"),
        ),
        _tool(
            "validate_working_release",
            "Validate the workspace-local working extraction pack. Validation does not compile, export, or activate.",
            {
                "artifact_folder": {"type": "string", "description": "Workspace root that owns the working release authoring truth under .vp/n."},
                "target_locale": {"type": "string", "description": "Optional locale to validate explicitly."},
            },
            required=("artifact_folder",),
        ),
        _tool(
            "compile_working_release",
            "Compile the workspace-local working extraction pack. Compile does not export or activate.",
            {
                "artifact_folder": {"type": "string", "description": "Workspace root that owns the working release authoring truth under .vp/n."},
                "target_locale": {"type": "string", "description": "Optional locale to compile explicitly."},
            },
            required=("artifact_folder",),
        ),
        _tool(
            "preview_working_release_impact",
            "Preview saved-source impact for the workspace-local working extraction pack. This reads impact only and does not validate, compile, export, or activate.",
            {
                "artifact_folder": {"type": "string", "description": "Workspace root that owns the working release authoring truth under .vp/n."},
            },
            required=("artifact_folder",),
        ),
        _tool(
            "create_working_release_package",
            "Create or update the workspace-local working release package by delegating exactly once to the Normalizer create_release_package action. This does not validate, compile, export, activate, inspect database state, or provide workflow advice.",
            {
                "artifact_folder": {"type": "string", "description": "Workspace root that owns the working release authoring truth under .vp/n."},
                "default_runtime_locale": {"type": "string", "description": "Optional default runtime locale."},
                "projection_ids": {"type": "array", "items": {"type": "string"}, "description": "Optional projection ids to include in the created working release package."},
            },
            required=("artifact_folder",),
        ),
        _tool(
            "review_bootstrap_release",
            "Review bootstrap goals against the workspace-local working extraction pack. This calls only the Normalizer review_bootstrap_release action and does not apply, validate, compile, export, or activate.",
            {
                "artifact_folder": {"type": "string", "description": "Workspace root that owns the working release authoring truth under .vp/n."},
                "goal": {"type": "string", "description": "Plain-language target for the release refinement."},
                "must_keep": {"type": "string", "description": "Information that must not be lost by the release refinement."},
                "noise_tolerance": {"type": "string", "enum": ["low", "medium", "high"], "description": "How conservative the bootstrap review should be."},
            },
            required=("artifact_folder", "goal", "must_keep", "noise_tolerance"),
        ),
        _tool(
            "apply_bootstrap_release",
            "Apply a reviewed bootstrap draft to the workspace-local working extraction pack. This calls only the Normalizer bootstrap_release_package action and does not validate, compile, export, or activate.",
            {
                "artifact_folder": {"type": "string", "description": "Workspace root that owns the working release authoring truth under .vp/n."},
                "goal": {"type": "string", "description": "Plain-language target for the release refinement."},
                "must_keep": {"type": "string", "description": "Information that must not be lost by the release refinement."},
                "noise_tolerance": {"type": "string", "enum": ["low", "medium", "high"], "description": "How conservative the bootstrap apply should be."},
                "user_confirmed": {"type": "boolean", "description": "Must be true; confirms that the user wants the source mutation."},
                "expected_candidate_fingerprint": {"type": "string", "description": "Optional candidate fingerprint from review_bootstrap_release."},
            },
            required=("artifact_folder", "goal", "must_keep", "noise_tolerance", "user_confirmed"),
        ),
        _tool(
            "review_data_informed_release",
            "Review one structured sample plus expected normalized artifact against the workspace-local working extraction pack. This calls only the Normalizer review_data_informed_release action and does not apply, validate, compile, export, or activate.",
            {
                "artifact_folder": {"type": "string", "description": "Workspace root that owns the working release authoring truth under .vp/n."},
                "structured_sample_path": {"type": "string", "description": "Path to the structured sample JSON."},
                "expected_normalized_path": {"type": "string", "description": "Path to the expected normalized JSON."},
                "original_reference_path": {"type": "string", "description": "Optional path to the original reference document."},
                "sample_label": {"type": "string", "description": "Optional user-facing label for this sample."},
            },
            required=("artifact_folder", "structured_sample_path", "expected_normalized_path"),
        ),
        _tool(
            "refine_working_release_from_sample",
            "Apply reviewed sample-driven refinements to the workspace-local working extraction pack. This calls only the Normalizer refine_release_package action and does not validate, compile, export, or activate.",
            {
                "artifact_folder": {"type": "string", "description": "Workspace root that owns the working release authoring truth under .vp/n."},
                "structured_sample_path": {"type": "string", "description": "Path to the structured sample JSON."},
                "expected_normalized_path": {"type": "string", "description": "Path to the expected normalized JSON."},
                "original_reference_path": {"type": "string", "description": "Optional path to the original reference document."},
                "sample_label": {"type": "string", "description": "Optional user-facing label for this sample."},
                "user_confirmed": {"type": "boolean", "description": "Must be true; confirms that the user wants the source mutation."},
                "expected_candidate_fingerprint": {"type": "string", "description": "Optional candidate fingerprint from review_data_informed_release."},
            },
            required=("artifact_folder", "structured_sample_path", "expected_normalized_path", "user_confirmed"),
        ),
        _tool(
            "export_working_release",
            "Export the workspace-local working extraction pack to an explicit JSON path. Export does not activate; output_path must not be under MCP state/semantic_releases.",
            {
                "artifact_folder": {"type": "string", "description": "Workspace root that owns the working release authoring truth under .vp/n."},
                "output_path": {"type": "string", "description": "Explicit JSON target path outside MCP state/semantic_releases."},
                "target_locale": {"type": "string", "description": "Optional locale to export explicitly."},
            },
            required=("artifact_folder", "output_path"),
        ),
    ]
