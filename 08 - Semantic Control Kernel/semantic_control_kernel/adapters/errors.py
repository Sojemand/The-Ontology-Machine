from __future__ import annotations


class AdapterError(RuntimeError):
    pass


class AdapterDispatchError(AdapterError):
    pass


class AdapterConfigurationError(AdapterError):
    pass
