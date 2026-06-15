"""Export and stats tests for Corpus Builder Vision."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from corpus_builder.export.adapter import write_csv, write_jsonl
from corpus_builder.export import export_csv, export_jsonl
from corpus_builder.loader import load_from_file as _load_from_file
from .semantic_release_test_support import build_release_variant


def _report_path(json_path: Path) -> Path:
    for suffix in (".vision_validation_report.json", ".validation_report.json"):
        candidate = json_path.with_name(json_path.name.replace(".structured.json", suffix))
        if candidate.exists():
            return candidate
    return json_path.with_name(json_path.name.replace(".structured.json", ".vision_validation_report.json"))


def load_from_file(db, json_path: Path, *, semantic_release=None):
    normalized_path = json_path.with_name(json_path.name.replace(".structured.json", ".structured.normalized.json"))
    return _load_from_file(
        db,
        normalized_path,
        _report_path(json_path),
        structured_path=json_path,
        semantic_release=semantic_release,
    )


def test_export_jsonl_and_csv(
    db,
    vision_structured,
    vision_normalized,
    vision_validation_report,
    make_input_pair,
    tmp_path,
):
    json_path = make_input_pair(
        "export_doc",
        vision_structured,
        vision_report=vision_validation_report,
        normalized=vision_normalized,
    )
    assert load_from_file(db, json_path, semantic_release=build_release_variant()).status == "loaded"

    jsonl_result = export_jsonl(db, tmp_path / "corpus.jsonl")
    csv_result = export_csv(db, tmp_path / "corpus.csv")

    assert jsonl_result.document_count == 1
    assert csv_result.document_count == 1

    jsonl_lines = (tmp_path / "corpus.jsonl").read_text(encoding="utf-8").strip().splitlines()
    exported = json.loads(jsonl_lines[0])
    assert exported["document_type"] == "invoice"
    assert exported["projection_id"] == "housing.default.v1"
    assert exported["materialization_state"] in {"current", "stale"}
    assert exported["fields"]["reference_number"] == "ENV 100002966355"
    assert exported["fields"]["invoice_number"] == "ENV 100002966355"
    assert exported["fields"]["currency"] == "EUR"
    assert exported["processing_state"] is not None
    assert exported["processing_state"]["projection_id"] == "housing.default.v1"
    assert {"projection_id", "projection_fingerprint", "materialization_state", "materialization_version"} <= exported["processing_state"].keys()
    assert exported["processing_state"]["materialization_state"] == exported["materialization_state"]
    assert isinstance(exported["entities"], list)
    assert exported["people"] == ["Norman Weiss"]
    assert exported["organizations"] == ["envia Mitteldeutsche Energie AG"]
    assert exported["document_promotions"]
    assert exported["document_promotion_values"]["billing_reference"] == "ENV 100002966355"

    with (tmp_path / "corpus.csv").open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == [
            "id",
            "file_name",
            "document_type",
            "category",
            "model_confidence",
            "validator_status",
            "language",
            "projection_id",
            "materialization_state",
            "materialization_version",
            "tags",
            "people",
            "organizations",
            "promotions_json",
        ]
        csv_row = next(reader)
    assert csv_row["document_type"] == "invoice"
    assert csv_row["organizations"] == "envia Mitteldeutsche Energie AG"
    assert csv_row["people"] == "Norman Weiss"
    assert csv_row["projection_id"] == "housing.default.v1"
    assert "billing_reference" in csv_row["promotions_json"]


def test_export_include_archived_controls_visibility(
    db,
    vision_structured,
    vision_validation_report,
    make_input_pair,
    tmp_path,
):
    first = dict(vision_structured)
    first["source"] = dict(vision_structured["source"])
    first["source"]["content_hash"] = "sha256:archived-first"
    second = dict(vision_structured)
    second["source"] = dict(vision_structured["source"])
    second["source"]["content_hash"] = "sha256:archived-second"

    assert load_from_file(db, make_input_pair("archived_old", first, vision_report=vision_validation_report)).status == "loaded"
    assert load_from_file(db, make_input_pair("archived_new", second, vision_report=vision_validation_report)).status == "archived_and_loaded"

    visible = export_jsonl(db, tmp_path / "visible.jsonl")
    all_docs = export_jsonl(db, tmp_path / "all.jsonl", include_archived=True)

    assert visible.document_count == 1
    assert all_docs.document_count == 2
    visible_ids = [json.loads(line)["id"] for line in (tmp_path / "visible.jsonl").read_text(encoding="utf-8").splitlines() if line]
    all_ids = [json.loads(line)["id"] for line in (tmp_path / "all.jsonl").read_text(encoding="utf-8").splitlines() if line]
    assert visible_ids == ["archived_new"]
    assert sorted(all_ids) == ["archived_new", "archived_old"]


def test_export_writes_empty_outputs_for_empty_database(db, tmp_path):
    jsonl_result = export_jsonl(db, tmp_path / "empty.jsonl")
    csv_result = export_csv(db, tmp_path / "empty.csv")

    assert jsonl_result.document_count == 0
    assert csv_result.document_count == 0
    assert (tmp_path / "empty.jsonl").read_text(encoding="utf-8") == ""
    assert (tmp_path / "empty.csv").read_text(encoding="utf-8").strip().startswith("id,file_name,document_type")


def _records_then_error():
    yield {"id": "new-doc", "file_name": "new.pdf"}
    raise RuntimeError("stop export")


def test_export_jsonl_failure_preserves_existing_final_file(tmp_path: Path) -> None:
    output = tmp_path / "corpus.jsonl"
    output.write_text('{"id":"old"}\n', encoding="utf-8")

    with pytest.raises(RuntimeError, match="stop export"):
        write_jsonl(output, _records_then_error())

    assert output.read_text(encoding="utf-8") == '{"id":"old"}\n'


def test_export_csv_failure_preserves_existing_final_file(tmp_path: Path) -> None:
    output = tmp_path / "corpus.csv"
    output.write_text("old\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="stop export"):
        write_csv(output, _records_then_error())

    assert output.read_text(encoding="utf-8") == "old\n"


def test_failed_export_to_absent_path_does_not_publish_final_file(tmp_path: Path) -> None:
    output = tmp_path / "missing.jsonl"

    with pytest.raises(RuntimeError, match="stop export"):
        write_jsonl(output, _records_then_error())

    assert not output.exists()
