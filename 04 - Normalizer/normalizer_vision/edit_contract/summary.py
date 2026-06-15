"""Owner-provided summary text for the Normalizer Edit Suite slot."""
from __future__ import annotations

from textwrap import dedent


def build_module_summary() -> str:
    return dedent(
        """
        NORMALIZER HELP

        Purpose
        This slot prepares the Normalizer's next-run behavior. It keeps prompt/settings editing local, and it edits taxonomy/projection semantics only through a copied compiled Semantic Release from an existing Artifact Tree.
        Governance terms: `taxonomy_sources`, `semantic_release_authoring`, `projection_hint`, `projection.selection.reason`, `routing.surface_signals`.

        Surface Guide
        - Settings (`normalizer.settings`): edits `config/config.yaml`, including projection routing thresholds.
        - Prompt Overrides (`normalizer.prompt_overrides`): edits `config/prompt_overrides.json` as a delta file.
        - Prompt Bundle (`normalizer.prompt_bundle`): edits `config/prompt_bundle.json` as the full base prompt payload.
        - Taxonomy / Projection Release (`normalizer.taxonomy_release_draft`): choose an Artifact Tree, recursively find a Semantic Release `release.json`, load it as a working copy, edit taxonomy terms and projections through structured controls, then Verify.
        - Debug Capabilities (`normalizer.debug_capabilities`): read-only view of public contract actions from `module-manifest.json`.

        Taxonomy / Projection Workflow
        1. Select an existing Artifact Tree.
        2. Load one discovered Semantic Release as a copy. The origin `release.json` is never mutated.
        3. Edit master taxonomy terms and projections in the structured editor; direct JSON authoring is not part of this workflow.
        4. Use `Verify` to rebuild projection fingerprints, release fingerprint, `projection_catalog`, `runtime_semantic_assets`, and the taxonomy analysis report.
        5. If a current Corpus DB is selected, Verify classifies whether the DB can be updated with auto refill or whether the edited release requires new DB materialization.
        6. Use `Write Copy` only after Verify succeeds. The verified copy is written under the Artifact Tree's `Semantic Release/drafts/edit_suite/<release_id>/release.json`.

        Verification Rules
        - Projection IDs are canonicalized and must match the Projection payloads.
        - Projection coverage lists must reference known taxonomy codes.
        - Routing text and `routing.surface_signals` must be present.
        - Promotion rules are validated against the master taxonomy.
        - Master taxonomy machine-field changes create a new master taxonomy release line; text-only changes preserve the origin line.

        Corpus Decision
        - `update_current_db_with_auto_refill`: the selected DB is compatible, but stale or projection-drift documents should be rematerialized.
        - `update_current_db`: the selected DB can use the verified release without refill.
        - `materialize_new_db`: the selected DB has missing projection IDs, foreign master IDs, or a different active master taxonomy release line.
        - `select_current_db`: Verify was run without a DB path, so only release integrity was checked.
        """
    ).strip()
