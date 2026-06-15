"""Debug-help resources for validator-facing modules."""

from __future__ import annotations

HELP_ENTRIES = {
    "validator": (
        "Validator Debug Guide",
        """OVERVIEW

This help applies only to the Validator inside the Debug tab.
Use this window when you want to validate one or more `*.structured.json` files in isolation and inspect the produced reports.

WHAT THIS DEBUG WINDOW IS GOOD FOR

- Run one concrete `*.structured.json` through the validator without starting the full pipeline.
- Validate a structured folder in batch and inspect every written report.
- Override individual check families before the run and confirm the effective config snapshot.
- Provide explicit raw evidence for files-route documents when you need deterministic file-profile validation.

WHAT THE CONTROLS IN THIS WINDOW DO

- Module: selects the target debug module. Keep it on Validator for this guide.
- Mode:
  - Single: validate one selected `*.structured.json`.
  - Batch: validate every matching `*.structured.json` below the selected folder.
- Input Path:
  - Single expects exactly one `*.structured.json`.
  - Batch expects a folder with validator-ready `*.structured.json` inputs.
  - This path goes directly into the Validator debug run. The main Input Folder from the Status tab is not used here.
- Raw JSON:
  - optional explicit `*.raw.json` for one files-route document in Single mode.
  - useful when the file profile should be checked against canonical raw evidence from the optimizer.
  - required when `processing.interpreter_profile` is `file` and you run one document in Single mode, unless you provide a matching Raw Folder instead.
- Raw Folder:
  - optional raw root for Batch mode.
  - the validator resolves matching raw evidence for files-route documents below this root.
  - required for Batch as soon as the selected structured tree contains at least one document with `processing.interpreter_profile = file`.
- Checks:
  - Free Text toggles `content.free_text` checks.
  - Context Scalars toggles context-field checks.
  - Content Fields toggles structured content-field checks.
  - Rows toggles row-level checks.
  - The effective configuration is written to `outputs/config_snapshot.json`.

MODE BEHAVIOR IN DEBUG

Single
- Runs `validator:debug_run` once for the selected `*.structured.json`.
- Writes exactly one report below `outputs/validation_reports/`.
- If the document uses `processing.interpreter_profile = file`, raw evidence is mandatory and missing raw evidence fails the run closed. Use Raw JSON for one concrete file or Raw Folder when the matching raw tree already exists.

Batch
- Runs `validator:debug_run` over the selected structured folder.
- Discovers `*.structured.json` recursively.
- Writes one report per document plus `outputs/report_index.json`.
- Pure vision batches can run without raw evidence.
- As soon as the batch contains at least one document with `processing.interpreter_profile = file`, Raw Folder becomes mandatory because the validator resolves file-profile raw evidence from that tree.

VALIDATOR LOGIC YOU SHOULD EXPECT

- The validator dispatches strictly over `processing.interpreter_profile`.
- Vision-profile documents are checked against context, fields, rows and `content.free_text`.
- Files-profile documents additionally use canonical raw evidence from `*.raw.json`.
- That means: `vision` does not need raw, `file` does.
- `*.structured.normalized.json` is downstream output from the Normalizer and is not valid Validator input.
- Check toggles affect only the current debug session and do not mutate the module defaults on disk.

WHAT YOU CAN INSPECT HERE

- Artifacts: validation reports, `config_snapshot.json`, `report_index.json`, and the session files `request.json`, `response.json`, `snapshot.json`, `result.json`, `run.log`.
- Preview tab: pretty-printed JSON or text for the currently selected artifact.
- run.log tab: session log with one line per validated document.
- Replay tab: optional offline loading of existing validator artifacts for comparison.
- Open Artifacts: open the written session tree in Explorer.

EXPECTED SESSION OUTPUTS

- outputs/validation_reports/*.vision_validation_report.json
- outputs/validation_reports/*.files_validation_report.json
- outputs/config_snapshot.json
- outputs/report_index.json
- session_root/request.json
- session_root/response.json
- session_root/snapshot.json
- session_root/result.json
- session_root/run.log

IMPORTANT NOTES

- Input Path in Single mode must point to `*.structured.json`, not to the original PDF/image and not to `*.structured.normalized.json`.
- For `processing.interpreter_profile = file`, raw evidence is mandatory. Without Raw JSON or Raw Folder the validator fails closed.
- For `processing.interpreter_profile = vision`, raw evidence is not required.
- The session monitor refreshes automatically while the debug session is running.
- Refresh forces an immediate poll. It does not restart the run.
- Cancel writes a cooperative cancel request.
- The config snapshot and report index make it easy to compare toggle combinations across repeated debug runs.""",
    ),
}
