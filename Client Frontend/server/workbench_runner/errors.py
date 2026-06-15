class WorkbenchPolicyError(PermissionError):
    pass


def deny(message: str) -> None:
    raise WorkbenchPolicyError(message)
