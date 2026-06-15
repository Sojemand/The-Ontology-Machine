from __future__ import annotations

from semantic_control_kernel.validation.debug_validation import validate_redaction_report, validate_support_bundle_manifest
from semantic_control_kernel.validation.recovery_validation import validate_support_bundle_ref


def validate_support_ref_payload(payload: object) -> None:
    if not isinstance(payload, dict):
        raise TypeError("Support bundle ref must be an object.")
    validate_support_bundle_ref(payload)


def validate_manifest_payload(payload: object) -> None:
    if not isinstance(payload, dict):
        raise TypeError("Support bundle manifest must be an object.")
    validate_support_bundle_manifest(payload)


def validate_redaction_report_payload(payload: object) -> None:
    if not isinstance(payload, dict):
        raise TypeError("Redaction report must be an object.")
    validate_redaction_report(payload)
