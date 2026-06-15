from __future__ import annotations


class PermissionPolicyError(ValueError):
    """Raised when the MCP permission policy is invalid."""


class PermissionDenied(RuntimeError):
    """Raised when the active agent level cannot use a tool."""


__all__ = ["PermissionPolicyError", "PermissionDenied"]
