from __future__ import annotations

from textwrap import dedent


USER_PROMPT = dedent(
    """
You are writing a clear user-facing sample analysis report. Use the same language as the user.

You receive user_report_samples_seed from a prior semantic sample-set analysis. The seed contains findings about
what the sample documents show together, how their content maps to taxonomy concepts, and how that content could
be covered by one or more projections.

Write a plain-language report for the user. The user should understand what was found and why it matters.

Return raw Markdown only. The first character of the response must be `#`.
Do not output JSON. Do not wrap the report in an object such as `{"report": "..."}`. Do not add code fences,
metadata, prefaces or explanations outside the report. Do not mention internal function names, schema versions,
downstream consumers, pipeline mechanics or implementation details.

This report is informational only. It must not claim that any taxonomy or projection will be created, changed,
validated or activated. It must not describe pipeline next steps. Later Kernel actions may use separate analysis
calls and may not exactly match this report.

Use exactly the report structure below. Keep the headings exactly as written.

Required headings:
# Sample Analysis Report
## 1. Overview
## 2. What The Samples Show
## 3. Taxonomy Perspective
## 4. Projection Perspective
## 5. Important Findings
## 6. Points To Review

Input:
{input_json}{validation_feedback_block}
    """
).strip()

OUTPUT_APPENDIX = dedent(
    """
- Output structure:
    - Plain text report.
    - Must use exactly these headings:
        - `# Sample Analysis Report`
        - `## 1. Overview`
        - `## 2. What The Samples Show`
        - `## 3. Taxonomy Perspective`
        - `## 4. Projection Perspective`
        - `## 5. Important Findings`
        - `## 6. Points To Review`
    - No JSON.
    - No JSON wrapper such as `{"report": "..."}`.
    - The first character must be `#`.
    - No code fence.
    - No metadata block.
    - No schema version.
    - No pipeline next steps.
    """
).strip()
