from tests.edit_contract_shared import *  # noqa: F401,F403


def test_source_operation_uses_unwrapped_pipeline_owner_request(tmp_project_root: Path) -> None:
    def fingerprint(payload: dict) -> str:
        import hashlib

        seed = dict(payload)
        seed["request_fingerprint"] = ""
        canonical = json.dumps(seed, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]

    owner_request = {
        "schema_version": "kernel.pipeline_owner_request.v1",
        "owner_action": "remove_projection_from_release",
        "workflow_run_id": "wr_contract_unwrap",
        "adapter_call_id": "adc_contract_unwrap",
        "requested_at": "2026-06-01T11:04:04Z",
        "target_identity": {"release_fingerprint": "sha256:release_before"},
        "release_ref": {
            "release_id": "semantic_release.default",
            "release_version": "2026-03-28.v6",
            "release_fingerprint": "sha256:release_before",
            "projection_refs": [
                {"projection_id": "projection.remove.v1", "projection_fingerprint": "sha256:remove"},
                {"projection_id": "projection.keep.v1", "projection_fingerprint": "sha256:keep"},
            ],
        },
        "projection_ids": ["projection.remove.v1"],
    }
    owner_request["request_fingerprint"] = fingerprint(owner_request)

    response = _run_contract(
        tmp_project_root,
        {
            "schema_version": "adapter.call_request.v1",
            "request_payload": owner_request,
        },
    )

    assert response["status"] == "ok"
    assert response["output_refs"]["remaining_projection_refs"] == [
        {"projection_id": "projection.keep.v1", "projection_fingerprint": "sha256:keep"}
    ]
    assert response["receipt_fields"]["owner_action"] == "remove_projection_from_release"

def test_export_and_activate_reject_non_json_bundle_paths(monkeypatch, tmp_project_root: Path) -> None:
    yaml_path = tmp_project_root / "output" / "semantic_release.yaml"
    bundle_dir = tmp_project_root / "output" / "bundle_dir"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(source_operations, "validate_release_package", lambda _root: {"status": "ok"})
    monkeypatch.setattr(
        source_operations,
        "ensure_compiled_taxonomy_assets",
        lambda _root: SimpleNamespace(release={"projection_ids": ["finance.default.v1"]}),
    )

    with pytest.raises(ValueError, match=r"output_path muss auf eine \.json-Datei zeigen"):
        source_operations.export_semantic_release(tmp_project_root, {"output_path": str(yaml_path)})

    with pytest.raises(ValueError, match=r"release_path muss auf eine \.json-Datei zeigen, nicht auf ein Verzeichnis"):
        source_operations.activate_semantic_release(
            tmp_project_root,
            {"release_path": str(bundle_dir), "corpus_db_path": str(tmp_project_root / "output" / "corpus.db")},
        )

def test_validate_surface_rejects_invalid_runtime_and_release_payloads(tmp_project_root: Path) -> None:
    forbidden = _run_contract(
        tmp_project_root,
        {
            "action": "validate_surface",
            "surface_id": "normalizer.settings",
            "value": {
                "timeout_seconds": 300,
                "max_retries": 3,
                "retry_delay_seconds": 5,
                "structured_outputs": True,
                "default_workers": 1,
                "max_structured_bytes": 10000000,
                "max_batch_files": 500,
                "max_batch_workers": 8,
                "taxonomy_profile_id": "housing.default.v1",
                "projection_hint_mode": "advisory",
                "projection_routing.field_signal_limit": 4,
                "projection_routing.row_signal_limit": 3,
                "projection_routing.cell_signal_limit": 6,
                "projection_routing.hint_confidence_low_threshold": 0.6,
                "projection_routing.hint_confidence_medium_threshold": 0.8,
                "projection_routing.hint_confidence_high_threshold": 0.9,
                "projection_routing.hint_confidence_low_bonus": 1,
                "projection_routing.hint_confidence_medium_bonus": 2,
                "projection_routing.hint_confidence_high_bonus": 3,
                "projection_routing.matched_signal_bonus_cap": 3,
                "projection_routing.hint_reject_margin": 3,
                "model": "gpt-5.4-mini",
            },
        },
    )
    unloaded_release = _run_contract(
        tmp_project_root,
        {
            "action": "validate_surface",
            "surface_id": "normalizer.taxonomy_release_draft",
            "value": {},
        },
    )

    assert forbidden["status"] == "error"
    assert "runtime" in forbidden["reason"]
    assert unloaded_release["status"] == "error"
    assert "Kein Semantic Release geladen" in unloaded_release["reason"]
