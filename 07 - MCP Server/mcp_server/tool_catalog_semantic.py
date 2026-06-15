from __future__ import annotations

from typing import Any

from .tool_catalog_utils import _artifact_properties, _enum, _tool


def semantic_tools() -> list[dict[str, Any]]:
    return [
        _tool(
            "inspect_pipeline_product_context",
            "Read a compact product-support context for the active Vision Pipeline: current workspace/database/input state plus the user-facing workflow catalog. This is read-only product advice support and never changes files, releases, or databases.",
            {
                "focus": {"type": "string", "description": "Optional user goal or product area to focus the context summary."},
                "include_workflow_catalog": {"type": "boolean", "default": True},
                "max_workflows": {"type": "integer", "minimum": 1, "default": 12},
            },
        ),
        _tool(
            "explain_pipeline_capabilities",
            "Explain what the active archive database and Vision Pipeline can be used for in plain language, using compact product semantics cards and goal playbooks. This is read-only and does not execute the recommended workflow.",
            {
                "question": {"type": "string", "description": "The user's product/capability question in their own words."},
                "goal": {"type": "string", "description": "Optional user goal if the turn is phrased as an objective rather than a question."},
                "focus": {"type": "string", "description": "Optional focus such as search, import, rule refinement, reimport, rebuild, or export."},
            },
        ),
        _tool(
            "recommend_pipeline_next_steps",
            "Recommend the next safe Pipeline workflow for a broad user goal, explaining why and listing alternatives. This is read-only product support and does not open or execute the recommended workflow.",
            {
                "goal": {"type": "string", "description": "The user's broad goal."},
                "question": {"type": "string", "description": "Optional question text when the goal is phrased as a question."},
                "focus": {"type": "string", "description": "Optional focus such as import, search, improve rules, rebuild, or export."},
                "known_context": {"type": "object", "description": "Optional compact state already observed by the Kernel or frontend."},
            },
        ),
        _tool(
            "assess_source_document_fit",
            "Inspect one user-provided source document and read the active Semantic Release on the current or explicit corpus DB, then return read-only evidence for whether the active projections/rules look suitable before import. This does not create, import, activate, rebuild, or modify anything.",
            {
                "source_document_path": {"type": "string", "description": "Absolute path to one source document/sample to compare against the active release and projections."},
                "corpus_db_path": {"type": "string", "description": "Optional corpus DB whose active release should be used; omit to use the active/default corpus context."},
                "sample_label": {"type": "string", "description": "Optional user-facing label for the sample."},
                "max_excerpt_chars": {"type": "integer", "minimum": 1, "default": 6000, "description": "Maximum source text characters to return through the sample inspection."},
                "timeout_seconds": {"type": "integer", "minimum": 1, "default": 120},
                "cleanup_days": {"type": "integer", "minimum": 0, "default": 1, "description": "Delete older inspection temp folders before running."},
            },
            required=("source_document_path",),
        ),
        _tool(
            "review_source_document_taxonomy_coverage",
            "Inspect one new source document against the active archive rules and return a read-only coverage/refinement review: document concepts, field or routing gaps, suggested working-release next step, and compatibility warnings for existing databases. This never imports the document, edits a release, activates rules, backfills, resets, or rebuilds a DB.",
            {
                "source_document_path": {"type": "string", "description": "Absolute path to one source document/sample whose contents should be checked for missed fields or taxonomy coverage gaps."},
                "corpus_db_path": {"type": "string", "description": "Optional corpus DB whose active release should be used; omit to use the active/default corpus context."},
                "artifact_folder": {"type": "string", "description": "Optional workspace/artifact folder that owns a working release to refine later; this review does not write to it."},
                "sample_label": {"type": "string", "description": "Optional user-facing label for the sample."},
                "max_excerpt_chars": {"type": "integer", "minimum": 1, "default": 6000, "description": "Maximum source text characters to return through the sample inspection."},
                "timeout_seconds": {"type": "integer", "minimum": 1, "default": 120},
                "cleanup_days": {"type": "integer", "minimum": 0, "default": 1, "description": "Delete older inspection temp folders before running."},
            },
            required=("source_document_path",),
        ),
        _tool(
            "review_source_sample_set_taxonomy_coverage",
            "Inspect all supported files in the active/current Pipeline Input folder against the active archive rules and return a read-only aggregate coverage/refinement review. The active Input folder is the only sample source; explicit file paths and ad-hoc sample folders are not accepted.",
            {
                "corpus_db_path": {"type": "string", "description": "Optional corpus DB whose active release should be used; omit to use the active/default corpus context."},
                "artifact_folder": {"type": "string", "description": "Optional workspace/artifact folder that owns a working release to refine later; this review does not write to it."},
                "max_samples": {"type": "integer", "minimum": 1, "default": 20, "description": "Maximum number of sample files to inspect."},
                "max_excerpt_chars": {"type": "integer", "minimum": 1, "default": 6000, "description": "Maximum source text characters to return per sample inspection."},
                "timeout_seconds": {"type": "integer", "minimum": 1, "default": 120},
                "cleanup_days": {"type": "integer", "minimum": 0, "default": 1, "description": "Delete older inspection temp folders before running."},
            },
        ),
        _tool(
            "prepare_source_samples_for_input",
            "Copy user-provided new sample files into the active Input folder for a later refined import. This does not select old DB originals, reset a database, activate rules, or start the pipeline; old originals must still use corpus_source_reimport.",
            {
                "source_document_paths": {"type": "array", "items": {"type": "string"}, "description": "Absolute paths to new sample files that should be queued in active Input."},
                "source_document_path": {"type": "string", "description": "Optional single extra source path."},
                "sample_folder": {"type": "string", "description": "Optional folder of new sample files to queue."},
                "max_samples": {"type": "integer", "minimum": 1, "default": 20, "description": "Maximum number of sample files to prepare."},
                "max_files": {"type": "integer", "minimum": 1, "description": "Optional maximum number of files to copy this time."},
                "max_preview": {"type": "integer", "minimum": 1, "default": 20},
                "conflict_policy": {"type": "string", "enum": ["rename", "skip"], "default": "rename", "description": "How to handle filename conflicts in Input."},
                "user_confirmed": {"type": "boolean", "description": "Must be true; confirms that new sample files may be copied into active Input."},
            },
            required=("user_confirmed",),
        ),
        _tool(
            "read_active_semantic_release",
            "Read which extraction-pack version is active on an explicit or default DB. Use this to confirm that the intended custom release, profile ids, and language are really attached to the database.",
            {"corpus_db_path": {"type": "string"}},
        ),
        _tool(
            "reset_active_corpus_db",
            "Reset the active corpus DB through Corpus Builder using a confirmation artifact.",
            {"corpus_db_path": {"type": "string"}, "confirmation_artifact_path": {"type": "string"}},
            required=("confirmation_artifact_path",),
        ),
        _tool(
            "load_semantic_release",
            "Stage/load an exported release in Corpus Builder.",
            {"release_path": {"type": "string"}, "corpus_db_path": {"type": "string"}},
            required=("release_path",),
        ),
        _tool(
            "semantic_audit",
            "Run Corpus Builder semantic audit for an explicit or default DB. This checks runtime consistency after activation; it does not by itself prove the custom release is semantically good for the user's documents.",
            {"corpus_db_path": {"type": "string"}},
        ),
        _tool(
            "activation_preflight",
            "Run visible Corpus Builder semantic release activation preflight.",
            {"release_path": {"type": "string"}, "corpus_db_path": {"type": "string"}},
            required=("release_path",),
        ),
        _tool(
            "activate_release_on_existing_db",
            "Activate an already exported semantic release on an existing DB through Corpus Builder only. Run activation_preflight separately before this when needed.",
            {
                "release_path": {"type": "string"},
                "corpus_db_path": {"type": "string"},
                "confirmation_artifact_path": {"type": "string"},
            },
            required=("release_path",),
        ),
        _tool(
            "backfill_stale",
            "Backfill stale semantic materialization after a compatible same-master release change. This rematerializes stored normalized artifacts against the currently active release; it does not re-run the Normalizer, does not import source files again, and cannot create values for newly added taxonomy fields. Do not use it for taxonomy-line changes; inspect and classify the revision with the dedicated revision tools first.",
            {
                "corpus_db_path": {"type": "string"},
                "document_ids": {"type": "array", "items": {"type": "string"}},
                "stale_only": {"type": "boolean", "default": True},
                "limit": {"type": "integer", "minimum": 1},
            },
        ),
        _tool(
            "merge_preflight",
            "Run Corpus Builder merge preflight.",
            {"source_db_path": {"type": "string"}, "target_db_path": {"type": "string"}},
            required=("source_db_path", "target_db_path"),
        ),
        _tool(
            "merge_corpora",
            "Merge corpus databases through the confirmation-based Corpus Builder contract.",
            {
                "source_db_path": {"type": "string"},
                "target_db_path": {"type": "string"},
                "snapshot_risk_confirmation_artifact_path": {"type": "string"},
                "collision_resolution_artifact_path": {"type": "string"},
            },
            required=("source_db_path", "target_db_path"),
        ),
    ]
