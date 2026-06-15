"""Debug-help resources for the merged optimizer module."""

from __future__ import annotations

HELP_ENTRIES = {
    "optimizer": (
        "Optimizer Debug Guide",
        """OVERVIEW

This help applies to the merged Optimizer inside the Debug tab.
Use this window when you want to run the optimizer in isolation and inspect its session outputs.

WHAT THIS DEBUG WINDOW IS GOOD FOR

- Preview which supported source files the optimizer would pick up before running a batch.
- Process one chosen file and inspect the produced raw JSON.
- Verify that page images are rendered as expected for scan/image and pageable-file profiles.
- Reproduce a small isolated optimizer run before debugging the interpreter or downstream modules.

MODE BEHAVIOR IN DEBUG

Scan
- Reads the Debug Host Input Path through the optimizer input catalog.
- Applies the current filters and shows a preview result.
- Does not generate raw_extracts or page_images.

Single
- Uses Source Path for one file.
- Writes session outputs below session_root/outputs/.
- Produces raw_extracts and page_images for that one file.

Batch
- Uses the Debug Host Input Path as the candidate set.
- Applies filters before processing starts.
- Produces session-relative outputs for all matched files.

IMPORTANT NOTES

- The merged optimizer dispatches internally by profile. Image files and scan-first documents use the vision profile; born-digital PDFs and pageable office/text files use the file profile.
- The Preview inspector is text-oriented. Rendered page images are best inspected through Open Artifacts.
- Scan is the safest first step when you want to validate filters before running Single or Batch.""",
    ),
}
