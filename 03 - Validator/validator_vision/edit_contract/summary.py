"""Owner-provided summary text for the Validator Edit Suite slot."""

from __future__ import annotations

from textwrap import dedent


def build_module_summary() -> str:
    return dedent(
        """
        VALIDATOR HELP

        Purpose
        This slot prepares Validator Vision for the next structured-payload validation run. The module reads the saved validation config, compares raw and structured evidence, and writes future validation reports for downstream review and normalization decisions.
        This slot is an authoring shell for owner-local files only. It does not launch validation or debug runs by itself.

        How To Read This Slot
        - Summary explains the module role, the two editable config slices, and the recommended first-time workflow.
        - Settings contains both editable slices from the same owner file `config/config.json`.
        - Prompts/Assets stays intentionally empty for this module because there is no editable prompt or asset surface here.
        - Operations shows read-only contract actions from `module-manifest.json`.
        - Preview/Drift is the review layer for current values, draft values, and diffs before save.

        Surface Guide
        - Settings (`validator.settings`): edits the `checks.*` and `match.*` slice inside `config/config.json`.
        - Report Preview Policy (`validator.report_preview_policy`): edits `flag_needs_review` and `max_issues_per_check` in the same owner file.
        - Debug Capabilities (`validator.debug_capabilities`): mirrors read-only contract actions such as `validate_document`, `healthcheck`, and `debug_run`.

        Checks Guide
        - `checks.free_text` toggles free-text validation.
        - `checks.context_scalars` toggles validation of context-level scalar values.
        - `checks.content_fields` toggles field-level structured content checks.
        - `checks.rows` toggles row-oriented validation logic.
        - Use these switches when one validation family is too strict, too noisy, or intentionally out of scope for a future run.

        Match Guide
        - `match.scalar_level` and `match.row_level` define the saved severity used when scalar or row mismatches are found.
        - `match.require_free_text` decides whether free-text evidence must be present before a match can pass.
        - `match.number_tolerance_absolute` sets the saved numeric tolerance for amount and quantity comparisons.
        - `match.min_string_length` and `match.min_compact_length` prevent very short values from creating noisy matches.
        - `match.context_fields`, `match.skip_content_fields`, and `match.skip_row_fields` shape which fields participate in matching.
        - `match.row_anchor_keys` defines the saved anchor keys used to align row-level evidence across payloads.

        Report Preview Guide
        - `flag_needs_review` controls whether future report-worthy findings should mark a case as needing review.
        - `max_issues_per_check` caps how many issues one check contributes to the report preview and report output.
        - This surface changes report-generation behavior only for future runs. Existing report files are not rewritten.

        Capabilities Guide
        - `Debug Capabilities` is a read-only reference to the public contract actions.
        - It documents what the module exposes, but it does not add run control to the Edit Suite.
        - Use it as orientation when you later test saved config changes through orchestrator-owned paths.

        Pipeline Impact
        - Validator runs after interpretation and before normalization-dependent review.
        - Changes here affect how strict future validation runs are, how many issues become visible, and whether a case is flagged for review.
        - Because the validator reads the same saved config file for both editable slices, save both slices in a coherent state before testing.

        What This Slot Does Not Control
        - Validation reports and debug session artifacts under `output/` stay outside this contract.
        - Run and debug execution stay orchestrator-owned.
        - Legacy local GUI and helper CLIs are not the editing surface for this phase.
        - Prompts/Assets is intentionally empty for this module.

        Recommended First-Time Workflow
        1. Start in Summary so you understand the split between validation checks, matching policy, and report preview policy.
        2. Open Settings first when you want to change what the validator checks or how it matches evidence.
        3. Open Report Preview Policy when the issue is about `needs_review` behavior or issue truncation.
        4. Use Preview/Drift before saving so both config slices still describe one coherent next-run policy.
        5. Use Debug Capabilities only as a read-only reminder of which contract actions are available for later orchestrator-owned testing.
        """
    ).strip()
