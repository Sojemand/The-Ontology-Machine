from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import MODULE_ROOT, _mkdir, _write_json


def _ensure_realistic_corpus() -> Path:
    root = MODULE_ROOT / "dev-tests" / "fixtures" / "go_live" / "realistic_corpus"
    if root.exists():
        shutil.rmtree(root)
    files: dict[str, str] = {
        "README.md": (
            "# Realistic Go-Live Corpus\n\n"
            "Synthetic-safe local regression corpus for Phase 20.\n"
            "All sources are invented, redacted and free of live secrets.\n"
        ),
        "sources/scan_invoice_alpha.txt": "Page 1\nInvoice Alpha\nClass: invoice\nAmount: 1200 EUR\n\nPage 2\nLine items and handwritten note.\n",
        "sources/scan_invoice_beta.txt": "Scan/Vision sample\nDocument class: invoice\nContains ambiguous payment reference for coverage testing.\n",
        "sources/file_contract_gamma.md": "# Service Contract Gamma\n\nDocument class: contract\n\n| Clause | Value |\n| --- | --- |\n| Term | 12 months |\n| Notice | 30 days |\n",
        "sources/file_report_delta.txt": "Born-digital report delta\nDocument class: report\nContains a narrative summary and no tabular section.\n",
        "sources/file_table_epsilon.csv": "column_a,column_b,column_c\nalpha,1,ok\nbeta,2,needs_projection\n",
        "normalized/scan_invoice_alpha.normalized.json": json.dumps({"history": "scan_vision", "document_class": "invoice", "rows": 4}, indent=2),
        "normalized/file_contract_gamma.normalized.json": json.dumps({"history": "born_digital_file", "document_class": "contract", "rows": 2}, indent=2),
        "artifact_tree/Corpus/filled_corpus.db": "synthetic placeholder for a filled database fixture\n",
        "artifact_tree/Corpus/empty_corpus.db": "synthetic placeholder for an empty database fixture\n",
        "artifact_tree/Semantic Release/semantic_release_manifest.json": json.dumps(
            {
                "schema_version": "kernel.semantic_release.fixture.v1",
                "release_id": "release_realistic",
                "release_version": "v1",
                "taxonomy_ids": ["invoice", "contract"],
                "projection_ids": ["core_fields", "table_rows"],
            },
            indent=2,
        ),
        "artifact_tree/Documents/logs/finalized_batch_manifest.json": json.dumps(
            {
                "schema_version": "kernel.pipeline_batch_manifest.v1",
                "pipeline_batch_id": "batch_realistic",
                "status": "finalized",
                "batch_kind": "manual_pipeline_run",
                "document_count": 5,
                "materialized_records": [{"record_id": "rec_1"}, {"record_id": "rec_2"}],
            },
            indent=2,
        ),
        "merge/compatible/source_a_release.json": json.dumps({"release_id": "merge_a", "compatibility": "compatible"}, indent=2),
        "merge/compatible/source_b_release.json": json.dumps({"release_id": "merge_b", "compatibility": "compatible"}, indent=2),
        "merge/collision/source_c_release.json": json.dumps({"release_id": "merge_c", "compatibility": "collision"}, indent=2),
        "merge/collision/source_d_release.json": json.dumps({"release_id": "merge_d", "compatibility": "collision"}, indent=2),
    }
    required_dirs = (
        root / "artifact_tree" / "Input",
        root / "artifact_tree" / "Corpus",
        root / "artifact_tree" / "Semantic Release",
        root / "artifact_tree" / "Documents" / "logs",
        root / "artifact_tree" / "Documents" / "normalized",
        root / "artifact_tree" / "Documents" / "originals",
        root / "artifact_tree" / "Documents" / "page_images",
        root / "artifact_tree" / "Documents" / "raw_extracts",
        root / "artifact_tree" / "Documents" / "requests",
        root / "artifact_tree" / "Documents" / "structured",
        root / "artifact_tree" / "Documents" / "validation",
        root / "artifact_tree" / "Error Cases",
    )
    for directory in required_dirs:
        _mkdir(directory)
    for relative, content in files.items():
        target = root / relative
        _mkdir(target.parent)
        target.write_text(content if content.endswith("\n") else f"{content}\n", encoding="utf-8")
    _write_realistic_fixture_manifest(root)
    return root


def _write_realistic_fixture_manifest(root: Path) -> None:
    entries: list[dict[str, Any]] = []
    for candidate in sorted(path for path in root.rglob("*") if path.is_file() and path.name != "fixture_manifest.json"):
        data = candidate.read_bytes()
        entries.append(
            {
                "relative_path": candidate.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(data).hexdigest(),
                "byte_count": len(data),
            }
        )
    payload = {
        "schema_version": "semantic_control_kernel.phase20.realistic_corpus_manifest.v1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_document_count": 5,
        "document_classes": ["invoice", "contract", "report"],
        "normalized_histories": ["scan_vision", "born_digital_file"],
        "has_multi_page_source": True,
        "has_table_like_source": True,
        "has_ambiguous_semantic_coverage": True,
        "filled_database_fixture": "artifact_tree/Corpus/filled_corpus.db",
        "empty_database_fixture": "artifact_tree/Corpus/empty_corpus.db",
        "artifact_tree_root": "artifact_tree/",
        "finalized_batch_manifest": "artifact_tree/Documents/logs/finalized_batch_manifest.json",
        "semantic_release_manifest": "artifact_tree/Semantic Release/semantic_release_manifest.json",
        "merge_compatible_pair": ["merge/compatible/source_a_release.json", "merge/compatible/source_b_release.json"],
        "merge_collision_pair": ["merge/collision/source_c_release.json", "merge/collision/source_d_release.json"],
        "row_counts": {
            "filled_database_rows": 2,
            "empty_database_rows": 0,
            "batch_manifest_records": 2,
        },
        "prohibited_secret_scan_results": [],
        "files": entries,
    }
    _write_json(root / "fixture_manifest.json", payload)
