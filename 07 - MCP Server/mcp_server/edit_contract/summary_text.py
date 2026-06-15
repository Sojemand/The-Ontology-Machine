from __future__ import annotations


def build_module_summary() -> str:
    return (
        "MCP SERVER PERMISSION SUMMARY\n\n"
        "The MCP Server is the local control plane for the Vision Pipeline. It exposes tools to an agent over local "
        "stdio and then delegates real work to the owning modules: Orchestrator, Normalizer, and Corpus Builder. "
        "Because those tools can read state, edit configuration, activate releases, reset corpora, or manage "
        "credentials, the server has its own permission policy.\n\n"
        "The important design rule is simple: permission is checked before any owner contract is started. If a tool "
        "is not allowed for the active agent level, the MCP Server stops the call locally. That keeps the owner "
        "modules clean, and it also prevents accidental state changes when a user only intended to inspect the "
        "pipeline.\n\n"
        "The Settings tab shows a guided editor for the Agent Permissions policy. New users should usually change "
        "only two things: the default permission level and the maximum permission cap. The default level says what a "
        "normal MCP session can do when no explicit environment override is present. The maximum cap is a hard "
        "ceiling: even if an environment variable asks for a higher level, the server refuses it.\n\n"
        "A conservative setup uses L0_READONLY or L1_AUTHOR as the default, then raises the maximum cap only when "
        "an operator intentionally needs release, corpus, or admin operations. A fully trusted local maintenance "
        "session may use L3_ADMIN, but that level should be understood as powerful: it includes owner-surface writes, "
        "Normalizer source debug escape hatches, runtime settings, credential writes, and audited secret reveal.\n\n"
        "The MCP Server also contains a local Support Monitor. It is not a code-patching robot for installed "
        "bytecode/runtime builds. Instead, the agent-visible workflow starts with a hard assessment step: missing "
        "paths, invalid input, missing configuration, expected preflight failures, permission denials, external "
        "dependency failures, and unknown issues are not reportable. Only unexpected exceptions, contract "
        "regressions, repeatable product failures, and data-corruption risks can receive an assessment_id that "
        "unlocks local preview/build/queue actions. This keeps the bridge back to developers explicit without "
        "pretending that production runtimes should diagnose every operator problem as a bug."
    )
