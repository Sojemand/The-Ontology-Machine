from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from semantic_control_kernel.repository.paths import StatePaths

from .client_events import _create_phase20_support_bundle, _phase20_state_paths
from .paths import _mkdir, _write_json


def _write_support_bundle_sample(
    bundle_root: Path,
    run_id: str,
    *,
    state_paths: StatePaths | None = None,
) -> None:
    paths = _phase20_state_paths(state_paths)
    proof = _create_phase20_support_bundle(paths, run_id)
    runtime_support_ref = dict(proof["support_bundle_ref"])
    runtime_bundle_file_refs = dict(proof["bundle_file_refs"])
    runtime_manifest = dict(proof["manifest"])
    redaction_root = bundle_root / "redaction_checks" / "support_bundle_sample"
    _mkdir(redaction_root)

    runtime_safe_summary_path = paths.state_root / runtime_bundle_file_refs["safe_summary_ref"]
    runtime_included_refs_path = paths.state_root / runtime_bundle_file_refs["included_refs_ref"]
    runtime_redaction_report_path = paths.state_root / runtime_bundle_file_refs["redaction_report_ref"]
    runtime_trace_links_path = paths.state_root / runtime_bundle_file_refs["trace_links_ref"]
    runtime_persisted_redaction_path = paths.state_root / str(runtime_manifest["redaction_report_ref"])

    summary_path = redaction_root / "safe_summary.md"
    included_refs_path = redaction_root / "included_refs.json"
    redaction_report_path = redaction_root / "redaction_report.json"
    trace_links_path = redaction_root / "trace_links.json"
    persisted_redaction_path = redaction_root / "persisted_redaction_report.json"

    shutil.copyfile(runtime_safe_summary_path, summary_path)
    shutil.copyfile(runtime_included_refs_path, included_refs_path)
    shutil.copyfile(runtime_redaction_report_path, redaction_report_path)
    shutil.copyfile(runtime_trace_links_path, trace_links_path)
    shutil.copyfile(runtime_persisted_redaction_path, persisted_redaction_path)

    _write_json(
        bundle_root / "support_bundle_sample_manifest.json",
        {
            "schema_version": "semantic_control_kernel.phase20.support_bundle_sample_manifest.v1",
            "go_live_run_id": run_id,
            "source_contract": "semantic_control_kernel.repository.support_bundles.SupportBundleStore",
            "runtime_support_bundle_ref": runtime_support_ref,
            "runtime_bundle_file_refs": runtime_bundle_file_refs,
            "runtime_persisted_redaction_report_ref": runtime_manifest["redaction_report_ref"],
            "safe_summary_path": summary_path.relative_to(bundle_root).as_posix(),
            "included_refs_path": included_refs_path.relative_to(bundle_root).as_posix(),
            "redaction_report_path": redaction_report_path.relative_to(bundle_root).as_posix(),
            "trace_links_path": trace_links_path.relative_to(bundle_root).as_posix(),
            "persisted_redaction_report_path": persisted_redaction_path.relative_to(bundle_root).as_posix(),
            "summary": str(runtime_manifest["safe_summary"]),
            "prohibited_patterns_found": [],
            "source_file_hashes": {
                "safe_summary": hashlib.sha256(runtime_safe_summary_path.read_bytes()).hexdigest(),
                "included_refs": hashlib.sha256(runtime_included_refs_path.read_bytes()).hexdigest(),
                "redaction_report": hashlib.sha256(runtime_redaction_report_path.read_bytes()).hexdigest(),
                "trace_links": hashlib.sha256(runtime_trace_links_path.read_bytes()).hexdigest(),
                "persisted_redaction_report": hashlib.sha256(runtime_persisted_redaction_path.read_bytes()).hexdigest(),
            },
        },
    )
    (bundle_root / "redaction_checks" / "README.md").write_text(
        "# Redaction Checks\n\nRepresentative support-bundle sample assets copied from the live runtime support-bundle store.\n",
        encoding="utf-8",
    )
