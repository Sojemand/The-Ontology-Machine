from __future__ import annotations

from phase20_go_live_support import latest_go_live_dir, load_json


def test_support_bundle_sample_manifest_points_to_safe_redacted_files() -> None:
    root = latest_go_live_dir()
    payload = load_json(root / "support_bundle_sample_manifest.json")

    for key in ("safe_summary_path", "included_refs_path", "redaction_report_path", "trace_links_path", "persisted_redaction_report_path"):
        assert (root / payload[key]).is_file()
    runtime_support_ref = payload["runtime_support_bundle_ref"]
    runtime_refs = payload["runtime_bundle_file_refs"]
    assert payload["source_contract"] == "semantic_control_kernel.repository.support_bundles.SupportBundleStore"
    assert runtime_support_ref["support_bundle_path"] == runtime_refs["manifest_ref"]
    assert runtime_support_ref["support_bundle_path"].startswith("support/bundles/")
    assert runtime_refs["safe_summary_ref"].startswith("support/bundles/")
    assert runtime_refs["included_refs_ref"].startswith("support/bundles/")
    assert runtime_refs["redaction_report_ref"].startswith("support/bundles/")
    assert runtime_refs["trace_links_ref"].startswith("support/bundles/")
    assert str(payload["runtime_persisted_redaction_report_ref"]).startswith("debug/redaction_reports/")
    assert payload["prohibited_patterns_found"] == []


def test_support_bundle_sample_contains_no_raw_prompts_provider_payloads_or_secrets() -> None:
    root = latest_go_live_dir()
    payload = load_json(root / "support_bundle_sample_manifest.json")
    summary_text = (root / payload["safe_summary_path"]).read_text(encoding="utf-8")
    included_refs = load_json(root / payload["included_refs_path"])
    redaction_report = load_json(root / payload["redaction_report_path"])
    persisted_redaction_report = load_json(root / payload["persisted_redaction_report_path"])
    combined = summary_text + "\n" + str(included_refs)

    assert "raw provider output" not in combined.lower()
    assert "raw prompt" not in combined.lower()
    assert "sk-" not in combined
    assert redaction_report["schema_version"] == "debug.redaction_report.v1"
    assert redaction_report["redaction_profile"]["raw_payloads_included"] is False
    assert redaction_report["raw_payload_refs_excluded"] == []
    assert redaction_report["redacted_secret_counts"] == {}
    assert redaction_report["redacted_path_counts"] == {}
    assert persisted_redaction_report["schema_version"] == "debug.redaction_report.v1"
    assert persisted_redaction_report["redaction_profile"]["raw_payloads_included"] is False
    assert persisted_redaction_report["raw_payload_refs_excluded"] == []
