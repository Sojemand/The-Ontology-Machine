"""Owner-provided summary text for the Interpreter Edit Suite slot."""

from __future__ import annotations

from textwrap import dedent


def build_module_summary() -> str:
    return dedent(
        """
        INTERPRETER HELP

        Purpose
        This slot prepares the headless Interpreter module for the next interpretation run. The module reads owner-local runtime policy, execution limits, and prompt assets, then turns canonical interpreter requests into structured output for downstream validation and normalization.
        This slot is an authoring shell for owner-local files only. It does not start `interpret_document` or `debug_run` by itself.

        How To Read This Slot
        - Summary explains the module role, the split between editable settings and read-only contract previews, and the recommended first workflow.
        - Settings contains the two editable slices stored in `config/.env`: Runtime Policy and Execution Limits.
        - Prompts/Assets contains the saved prompt bundle under `config/prompt_bundle`.
        - Operations shows read-only contract actions from `module-manifest.json`.
        - Preview/Drift contains the read-only Output Contract Preview plus current, draft, and diff views for editable surfaces.

        Surface Guide
        - Runtime Policy (`interpreter.runtime_policy_env`): edits the non-secret runtime and path values in `config/.env`.
        - Execution Limits (`interpreter.execution_limits`): edits the saved request-size, worker, retry, and timeout limits in the same `config/.env`.
        - Prompt Bundle (`interpreter.prompt_bundle`): edits the owner-local prompt asset bundle under `config/prompt_bundle`.
        - Output Contract Preview (`interpreter.output_contract_preview`): read-only view of the canonical output schema and persisted output rules.
        - Debug Capabilities (`interpreter.debug_capabilities`): read-only contract summary for `interpret_document`, `healthcheck`, `debug_run`, and `generate_llm`.

        Runtime Policy Guide
        - `LOG_LEVEL` controls the saved local log verbosity for future runs.
        - `DEBUG_BUNDLE_DIR` is the optional saved directory for debug bundles when you intentionally keep them.
        - `PAGE_ASSET_ALLOWED_ROOTS` stores the saved allowlist for local page-asset roots. In this module it remains a string field and uses the platform path separator.
        - `OPENAI_API_BASE_URL` is the advanced saved endpoint override. OAuth-based runs can still override the effective endpoint at runtime.
        - These values change future runtime behavior only after the owner file is saved.

        Execution Limits Guide
        - `MAX_WORKERS` controls local worker concurrency.
        - `MAX_PAGE_ASSETS`, `MAX_PAGE_ASSET_BYTES`, and `MAX_REQUEST_ASSET_BYTES` cap how much page-asset data a future request may carry.
        - `TIMEOUT_SECONDS`, `MAX_RETRIES`, and `RETRY_DELAY_SECONDS` control retry and timeout behavior for future provider calls.
        - OCR/raw blocks and page images intentionally pass through after the asset limits above; this surface does not trim prompt sections or expected output rows.

        Prompt Bundle Guide
        - `system_prompt_md` controls the reusable system message.
        - `user_prompt_rules_md` controls the reusable extraction rules that follow the fixed guideline layer.
        - `output_schema_json` is editable as a saved asset but must remain aligned with the canonical code-owned output schema.
        - `projection_hint_policy_md` controls the saved guidance around projection hints and the request catalog.
        - Prompt edits change the next-run instruction text only. Existing structured outputs do not change retroactively.

        Output Contract Guide
        - `Output Contract Preview` is the safe place to inspect the read-only canonical schema the module must satisfy.
        - It shows the model-facing output contract plus the persisted output additions such as the required `source` block.
        - Use this surface to confirm that prompt edits still match the hard contract boundary before you save.

        Capabilities Guide
        - `Debug Capabilities` mirrors the public contract actions and debug hooks from the manifest.
        - These links are references, not launch controls. Run and debug execution remain outside the Edit Suite workflow.
        - Save owner-file changes before you test them through orchestrator-owned run paths.

        What This Slot Does Not Control
        - Auth, model choice, `MAX_OUTPUT_TOKENS`, and thinking remain orchestrator-owned.
        - `processing.interpreter_profile` stays a downstream field and is not edited here.
        - This slot does not edit runtime manifests, installer payloads, or debug session artifacts.
        - It does not retroactively rewrite existing structured outputs.

        Recommended First-Time Workflow
        1. Start in Summary so you understand the split between editable env settings, prompt assets, and read-only contract previews.
        2. Open Runtime Policy first when the problem is about logging, debug bundles, asset roots, or endpoint boundaries.
        3. Open Execution Limits when the issue is about timeouts, retries, asset size, or prompt budgets.
        4. Open Prompt Bundle only when you want to change reusable instruction text.
        5. Check Output Contract Preview before saving whenever you touched prompt assets.
        6. Use Debug Capabilities only as a read-only reminder of what the module exposes for later orchestrator-owned testing.
        """
    ).strip()
