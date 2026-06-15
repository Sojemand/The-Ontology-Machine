"""Bootstrap error types."""


class ModuleRegistryError(RuntimeError):
    """Raised when the bundled module registry or a module manifest is invalid."""


class StartupPrerequisiteError(RuntimeError):
    """Raised when the standalone orchestrator bundle is incomplete for startup."""
