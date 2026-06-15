"""Shared contract-runtime boundary for owner-provided modules."""

from .adapter import invoke_module_contract, invoke_owner_contract

__all__ = ["invoke_module_contract", "invoke_owner_contract"]
