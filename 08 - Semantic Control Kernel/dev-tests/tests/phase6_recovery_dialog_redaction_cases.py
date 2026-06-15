from __future__ import annotations

from pathlib import Path

from phase6_recovery_dialog_support import SNAPSHOT, TARGET, recovery_option, service_for


def test_support_bundle_dialog_redacts_raw_technical_payloads(tmp_path: Path) -> None:
    service = service_for(tmp_path)

    result = service.request_recovery_dialog(
        recovery_dialog_type="support_bundle_dialog",
        recovery_id="rcv_support",
        workflow_run_id="wr_phase6",
        function_or_route="phase6_support_route",
        target_identity=TARGET,
        state_snapshot_identity=SNAPSHOT,
        user_visible_title="Traceback with secret sk-test",
        user_visible_summary="Traceback\nsafe summary line\nraw_provider_response should not appear",
        user_visible_cause="api_key leaked in raw stack trace",
        recovery_effect="Open support bundle only.",
        risk_class="support",
        options=[
            recovery_option(
                "rcv_support",
                "support_bundle_dialog",
                label="Support",
                description="Open support bundle only.",
                risk_class="support",
                owner="support_surface",
                recovery_action_type="open_support_bundle",
                effect="open_support_bundle",
                extra={"raw_stack_trace": "Traceback...", "raw_llm_response": "{bad}"},
            )
        ],
    )
    payload_text = str(result.request.to_dict()).casefold()

    assert "traceback" not in payload_text
    assert "raw_stack_trace" not in payload_text
    assert "raw_provider_response" not in payload_text
    assert "raw_llm_response" not in payload_text
    assert "sk-test" not in payload_text


def test_support_bundle_dialog_recursively_filters_nested_technical_payloads(tmp_path: Path) -> None:
    service = service_for(tmp_path)

    result = service.request_recovery_dialog(
        recovery_dialog_type="support_bundle_dialog",
        recovery_id="rcv_support_nested",
        workflow_run_id="wr_phase6",
        function_or_route="phase6_support_route",
        target_identity=TARGET,
        state_snapshot_identity=SNAPSHOT,
        user_visible_title="Support",
        user_visible_summary="Safe support summary.",
        user_visible_cause="A final error requires support.",
        recovery_effect="Open support bundle only.",
        risk_class="support",
        options=[
            recovery_option(
                "rcv_support_nested",
                "support_bundle_dialog",
                label="Support",
                description="Support safe line.",
                risk_class="support",
                owner="support_surface",
                recovery_action_type="open_support_bundle",
                effect="open_support_bundle",
                agent_tool="kernel_open_support_bundle",
                extra={
                    "debug": {
                        "raw_stack_trace": "Traceback: secret sk-test",
                        "notes": ["safe line", "raw_llm_response: {bad}"],
                    }
                },
            )
        ],
        allowed_agent_tools=("kernel_open_support_bundle",),
    )
    payload_text = str(result.request.to_dict()).casefold()

    assert "raw_stack_trace" not in payload_text
    assert "raw_llm_response" not in payload_text
    assert "traceback" not in payload_text
    assert "sk-test" not in payload_text
    assert "support safe line" in payload_text
