from __future__ import annotations


class StateRepositoryError(Exception):
    """Base class for Kernel state repository failures."""


class StateRootError(StateRepositoryError):
    pass


class StatePathEscapeError(StateRootError):
    pass


class StateFileLockUnavailableError(StateRepositoryError):
    pass


class StateFileReadUnavailableError(StateRepositoryError):
    pass


class AtomicWriteError(StateRepositoryError):
    pass


class StateReadAfterWriteError(AtomicWriteError):
    pass


class StateCorruptionError(StateRepositoryError):
    pass


class ImmutableReceiptError(StateRepositoryError):
    pass


class DuplicateStateObjectError(StateRepositoryError):
    pass


class LockConflictError(StateRepositoryError):
    pass


class LockExpiredError(StateRepositoryError):
    pass


class StaleLockRequiresRecoveryError(StateRepositoryError):
    pass


class TargetIdentityMismatchError(StateRepositoryError):
    pass


class ResumeStateNotFoundError(StateRepositoryError):
    pass


class BindingConflictError(StateRepositoryError):
    pass


class BindingNotFoundError(StateRepositoryError):
    pass


class KernelStateResetError(StateRepositoryError):
    pass
