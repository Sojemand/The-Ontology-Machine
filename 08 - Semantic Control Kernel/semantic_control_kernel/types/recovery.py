from __future__ import annotations

from semantic_control_kernel.types.base import make_contract_types


_CONTRACT_TYPES = (
    ("RecoveryEvent", "kernel.recovery_event.v1"),
    ("RecoveryOption", "kernel.recovery_option.v1"),
    ("Phase13RecoveryReceipt", "kernel.recovery_receipt.v1"),
    ("SupportBundleRef", "kernel.support_bundle_ref.v1"),
)

globals().update(make_contract_types(_CONTRACT_TYPES, __name__))


RECOVERY_EVENT_SCHEMA_VERSION = RecoveryEvent.SCHEMA_VERSION
RECOVERY_OPTION_SCHEMA_VERSION = RecoveryOption.SCHEMA_VERSION
RECOVERY_RECEIPT_SCHEMA_VERSION = Phase13RecoveryReceipt.SCHEMA_VERSION
SUPPORT_BUNDLE_REF_SCHEMA_VERSION = SupportBundleRef.SCHEMA_VERSION
