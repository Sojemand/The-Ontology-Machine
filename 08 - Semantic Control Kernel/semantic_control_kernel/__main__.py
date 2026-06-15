from __future__ import annotations

import argparse
import sys

from semantic_control_kernel.bootstrap import runtime_report


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] not in {"--help", "-h", "--runtime-report", "--root", "--strict"}:
        print(f"Unsupported Semantic Control Kernel command: {args[0]}", file=sys.stderr)
        return 2

    parser = argparse.ArgumentParser(
        prog="semantic_control_kernel",
        description="Semantic Control Kernel runtime shell.",
    )
    parser.add_argument(
        "--runtime-report",
        action="store_true",
        help="Run the runtime preflight report and print one JSON object.",
    )
    parser.add_argument("--root", help="Module root for --runtime-report.")
    parser.add_argument("--strict", action="store_true", help="Fail non-zero when any preflight check fails.")
    parsed = parser.parse_args(args)

    if parsed.runtime_report:
        if not parsed.root:
            print("--runtime-report requires --root <module_root>", file=sys.stderr)
            return 2
        report_args = ["--root", parsed.root]
        if parsed.strict:
            report_args.append("--strict")
        return runtime_report.main(report_args)

    if parsed.root or parsed.strict:
        print("--root and --strict are valid only with --runtime-report", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
