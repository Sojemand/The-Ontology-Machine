"""Debug-help resources for the merged interpreter module."""

from __future__ import annotations

HELP_ENTRIES = {
    "interpreter": (
        "Interpreter Debug Guide",
        """OVERVIEW

This help applies to the merged Interpreter inside the Debug tab.
Use this window when you want to inspect the full debug chain from Optimizer through Request Enrichment into the interpreter.

WHAT THIS DEBUG WINDOW IS GOOD FOR

- Preview which upstream optimizer candidates would be processed before any LLM call.
- Run one chosen source file through optimizer, Request Enrichment, and interpreter in one isolated session.
- Run a small interpreter batch over the Debug Host Input Path and inspect every generated request and structured output.
- Verify exactly which orchestrator-owned injections happen before the interpreter subprocess starts.

MODE BEHAVIOR IN DEBUG

Scan
- Runs only `optimizer:scan_debug_input`.
- Uses the Debug Host Input Path.
- Does not create optimizer outputs, no Request Enrichment, and no interpreter call.

Single
- Runs `optimizer:debug_run -> Request Enrichment -> interpreter:debug_run`.
- Uses Source Path for the concrete original source file before the optimizer.
- Do not point Source Path at `raw_extracts/*.raw.json`; that is optimizer output, not interpreter input.
- Writes one canonical request below `outputs/requests/.../interpreter.request.json`.

Batch
- Runs `optimizer:debug_run -> Request Enrichment -> interpreter:debug_run`.
- Uses the Debug Host Input Path as candidate set.
- Request Enrichment writes one request per optimizer raw output below `outputs/requests/.../interpreter.request.json`.
- The interpreter batch step reads that request tree recursively and writes structured outputs below `outputs/structured_output/...`.

IMPORTANT NOTES

- The merged interpreter dispatches internally by `context.interpreter_profile` in the generated request.
- Models tab injects `model` and `max_output_tokens` immediately before the interpreter subprocess starts.
- Credentials tab injects the interpreter authentication environment via orchestrator-owned ephemeral env vars.
- Request Enrichment injects `projection_catalog` from the active runtime-semantics bundle into every interpreter request.
- Scan is the safest first step when you want to verify the upstream candidate set before spending LLM calls.""",
    ),
}
