from __future__ import annotations

import json

from corpus_builder.embeddings import build_embedding_text
from corpus_builder.embeddings.domain import build_embedding_chunks
from corpus_builder.embeddings.types import EvidenceAtomSource, ExtractedFieldSource, ExtractedRowSource, PendingEmbeddingSource, PromotionSource


def test_build_embedding_text_is_curated_not_raw_json(vision_structured):
    text = build_embedding_text(vision_structured, max_chars=4000)

    assert "Ihre Schlussrechnung" in text
    assert "Zu zahlender Betrag 318,79 EUR" in text
    assert "_source_refs" not in text
    assert "source_ref_validation" not in text
    assert len(text) <= 4000


def test_embedding_chunks_split_at_700_without_dropping_source_text():
    segment_atoms = tuple(
        EvidenceAtomSource(
            atom_id=index + 1,
            atom_type="segment",
            page=1,
            json_path=f"$.content.segments[{index}]",
            text_value=f"segment-marker-{index:02d} " + " ".join(f"s{index:02d}_{token:02d}" for token in range(8)),
        )
        for index in range(24)
    )
    row_tokens = " ".join(f"rowtoken{index:03d}" for index in range(90))
    field_tokens = " ".join(f"fieldtoken{index:03d}" for index in range(90))
    source = PendingEmbeddingSource(
        document_id="chunk_split_doc",
        normalized_json="{}",
        document_type="Test",
        promotions=(
            PromotionSource(
                promotion_id=10,
                slot="artifact_code",
                slot_label="Artifact Code",
                value_type="string",
                query_role="identifier",
                display_value="FANTASY-77",
                source_path="content.fields.artifact_code",
            ),
        ),
        evidence_atoms=segment_atoms,
        rows=(ExtractedRowSource(row_id=1, row_index=0, row_json=json.dumps({"details": row_tokens})),),
        fields=(ExtractedFieldSource(field_id=1, key="details", value=field_tokens),),
    )

    chunks = build_embedding_chunks(source, max_chars=12000)

    assert len(chunks) > 3
    assert all(len(chunk.text) <= 700 for chunk in chunks)
    combined = " ".join(chunk.text for chunk in chunks)
    assert "segment-marker-00" in combined
    assert "segment-marker-23" in combined
    assert "rowtoken000" in combined
    assert "rowtoken089" in combined
    assert "fieldtoken000" in combined
    assert "fieldtoken089" in combined
    assert "FANTASY-77" in combined
