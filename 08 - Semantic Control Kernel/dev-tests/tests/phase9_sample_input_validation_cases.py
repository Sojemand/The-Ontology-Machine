from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.workflows.database_creation.custom_projection import validate_projection_samples
from semantic_control_kernel.workflows.database_creation.optimizer_sample_normalizer import analyze_sample_input_from_optimizer_raw
from semantic_control_kernel.workflows.database_creation.sample_input_adapter import sample_refs_from_input

from _phase9_fakes import target_for
from phase9_sample_input_support import FailingOrchestratorAdapter


def test_sample_inspection_owner_error_becomes_specific_blocker(tmp_path: Path) -> None:
    target = target_for(tmp_path)
    input_root = Path(target.input_path)
    input_root.mkdir(parents=True)
    (input_root / "invoice.pdf").write_bytes(b"%PDF-1.7")

    refs = sample_refs_from_input(
        target=target,
        orchestrator_adapter=FailingOrchestratorAdapter(),
        workflow_run_id="wr_sample_error",
    )

    blocker = validate_projection_samples(target=target, sample_refs=refs)

    assert refs[0]["sample_inspection_error"]["summary"] == "optimizer_ocr Modell fehlt."
    assert blocker is not None
    assert "optimizer_ocr Modell fehlt" in blocker.user_visible_summary


def test_optimizer_normalizer_deduplicates_page_and_aggregate_blocks(tmp_path: Path) -> None:
    source = tmp_path / "sample.pdf"
    source.write_bytes(b"%PDF-1.7")
    raw = {
        "schema_version": "optimizer_raw_v2",
        "optimizer_profile": "file",
        "context": {"page_number": 1},
        "ocr_reference": {
            "blocks": [
                {"id": "b1", "type": "paragraph", "layout_label": "header", "value": "Rechnung", "position": {"page": 1}}
            ]
        },
    }

    sample = analyze_sample_input_from_optimizer_raw(
        sample_id="sample_001",
        source_path=source,
        raw_payloads=[raw, raw],
        raw_extract_paths=["page.raw.json", "aggregate.raw.json"],
    )

    assert len(sample["document"]["extracted_content"]["sections"]) == 1
