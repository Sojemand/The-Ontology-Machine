from __future__ import annotations


KERNEL_AUTHORING_TRUTH = {
    "locks": "Semantic Control Kernel state/locks/",
    "resume_state": "Semantic Control Kernel state/resume/",
    "pending_confirmations": "Semantic Control Kernel state/pending_confirmations/",
    "pending_interactions": "Semantic Control Kernel state/pending_interactions/",
    "receipts": "Semantic Control Kernel state/receipts/",
    "progress_events": "Semantic Control Kernel state/events/progress/",
    "mirror_events": "Semantic Control Kernel state/events/mirror/",
    "event_scoped_tool_availability": "Semantic Control Kernel state/events/tool_availability/",
    "database_artifact_binding": "Semantic Control Kernel state/bindings/",
    "kernel_held_attach_state": "Semantic Control Kernel state/attach_states/",
}

OWNER_EVIDENCE_ONLY = {
    "corpus_database_content": "Corpus Builder / database owner",
    "artifact_tree_documents": "Artifact Tree / Pipeline owner modules",
    "semantic_release_package_content": "Semantic Release artifact owner / Corpus Builder activation contract",
    "active_runtime_release_pointer": "Corpus Builder / Pipeline activation owner",
    "mcp_server_state": "07 - MCP Server",
    "client_frontend_state": "Client Frontend",
}

RESET_ARCHIVE_BOUNDARY = {
    "archives": (
        "workflow_runs/active",
        "resume",
        "pending_confirmations/active",
        "pending_interactions/active",
        "locks/active",
        "events/tool_availability",
    ),
    "preserves": (
        "bindings",
        "attach_states",
        "receipts",
        "support",
        "events/progress",
        "events/mirror",
        "quarantine",
    ),
}
