from __future__ import annotations


class KernelContractError(ValueError):
    pass


class UnknownSchemaVersionError(KernelContractError):
    pass


class SchemaVersionMismatchError(KernelContractError):
    pass


class MissingRequiredFieldError(KernelContractError):
    pass


class UnknownFieldError(KernelContractError):
    pass


class EnumValidationError(KernelContractError):
    pass


class ContractRoundTripError(KernelContractError):
    pass


class RawDictBoundaryError(KernelContractError):
    pass
