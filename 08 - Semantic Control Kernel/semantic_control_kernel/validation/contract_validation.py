from __future__ import annotations

from semantic_control_kernel.types.base import KernelContract
from semantic_control_kernel.types.registry import CONTRACT_REGISTRY, ContractRegistryEntry
from semantic_control_kernel.validation.contract_engine import (
    parse_contract,
    serialize_contract,
    validate_contract,
    validate_contract_roundtrip,
)
from semantic_control_kernel.validation.contract_errors import (
    ContractRoundTripError,
    EnumValidationError,
    KernelContractError,
    MissingRequiredFieldError,
    RawDictBoundaryError,
    SchemaVersionMismatchError,
    UnknownFieldError,
    UnknownSchemaVersionError,
)
from semantic_control_kernel.validation.contract_primitives import (
    reject_unknown_fields,
    require_required_fields,
    require_schema_version,
    validate_enum,
)
from semantic_control_kernel.validation.contract_rules import (
    CLIENT_FRONTEND_EVENT_NESTED_CONTRACTS,
    CLOSED_MAPPING_FIELD_RULES,
    CONSTANT_FIELD_RULES,
    ENUM_FIELD_RULES,
    FIELD_KIND_RULES,
    INTERACTION_EXPIRATION_POLICY_ALLOWED_FIELDS,
    LOCK_EXPIRY_POLICY_ALLOWED_FIELDS,
    PIPELINE_BATCH_NESTED_SHAPES,
    REQUIRED_FIELD_PATH_RULES,
    STATE_SNAPSHOT_IDENTITY_ALLOWED_FIELDS,
    TARGET_IDENTITY_ALLOWED_FIELDS,
    EnumRuleMap,
)

__all__ = [
    "CLIENT_FRONTEND_EVENT_NESTED_CONTRACTS",
    "CLOSED_MAPPING_FIELD_RULES",
    "CONSTANT_FIELD_RULES",
    "CONTRACT_REGISTRY",
    "ContractRegistryEntry",
    "ContractRoundTripError",
    "ENUM_FIELD_RULES",
    "EnumRuleMap",
    "EnumValidationError",
    "FIELD_KIND_RULES",
    "INTERACTION_EXPIRATION_POLICY_ALLOWED_FIELDS",
    "KernelContract",
    "KernelContractError",
    "LOCK_EXPIRY_POLICY_ALLOWED_FIELDS",
    "MissingRequiredFieldError",
    "PIPELINE_BATCH_NESTED_SHAPES",
    "REQUIRED_FIELD_PATH_RULES",
    "RawDictBoundaryError",
    "STATE_SNAPSHOT_IDENTITY_ALLOWED_FIELDS",
    "SchemaVersionMismatchError",
    "TARGET_IDENTITY_ALLOWED_FIELDS",
    "UnknownFieldError",
    "UnknownSchemaVersionError",
    "parse_contract",
    "reject_unknown_fields",
    "require_required_fields",
    "require_schema_version",
    "serialize_contract",
    "validate_contract",
    "validate_contract_roundtrip",
    "validate_enum",
]
