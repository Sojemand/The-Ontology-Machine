"""Pipeline exceptions with stable import names."""


class OrchestratorCancelled(RuntimeError):
    """Raised when the active run should stop early."""


class OrchestratorBusyError(RuntimeError):
    """Raised when another orchestrator process already holds the state lock."""
