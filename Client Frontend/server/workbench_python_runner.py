import builtins
import sys

from workbench_runner.errors import WorkbenchPolicyError
from workbench_runner.guards import install_guards


def main() -> int:
    install_guards()
    source = sys.stdin.read()
    globals_dict = {"__name__": "__main__", "__builtins__": builtins}
    exec(compile(source, "<workbench>", "exec"), globals_dict, globals_dict)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except WorkbenchPolicyError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
