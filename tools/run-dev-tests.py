from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


PIPELINE_ROOT = Path(__file__).resolve().parents[1]
TOOLS_SUITE = PIPELINE_ROOT / "tools" / "dev-tests" / "suite.json"
PREFERRED_ORDER = (
    "00 - Orchestrator",
    "01 - Optimizer",
    "02 - Interpreter",
    "03 - Validator",
    "04 - Normalizer",
    "05 - Corpus Builder",
    "06 - Edit Suite",
    "07 - MCP Server",
    "08 - Semantic Control Kernel",
    "Client Frontend",
    "tools",
)


@dataclass(frozen=True)
class Suite:
    name: str
    display_name: str
    kind: str
    suite_dir: Path
    bootstrap_script: Path
    run_script: Path
    aliases: tuple[str, ...]


def _discover_suite_files() -> list[Path]:
    suite_files = [path.resolve() for path in sorted(PIPELINE_ROOT.glob("*/dev-tests/suite.json"))]
    if TOOLS_SUITE.exists() and TOOLS_SUITE.resolve() not in suite_files:
        suite_files.append(TOOLS_SUITE)
    return suite_files


def _load_suite(path: Path) -> Suite:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    suite_dir = path.parent
    aliases = tuple(str(value) for value in payload.get("aliases", []))
    return Suite(
        name=str(payload.get("name") or suite_dir.parent.name),
        display_name=str(payload.get("display_name") or payload.get("name") or suite_dir.parent.name),
        kind=str(payload.get("kind") or "unknown"),
        suite_dir=suite_dir,
        bootstrap_script=(suite_dir / str(payload.get("bootstrap_script", "bootstrap.bat"))).resolve(),
        run_script=(suite_dir / str(payload.get("run_script", "run-tests.bat"))).resolve(),
        aliases=aliases,
    )


def _sort_key(suite: Suite) -> tuple[int, str]:
    try:
        index = PREFERRED_ORDER.index(suite.name)
    except ValueError:
        index = len(PREFERRED_ORDER)
    return index, suite.name.casefold()


def _discover_suites() -> list[Suite]:
    suites = [_load_suite(path) for path in _discover_suite_files()]
    suites.sort(key=_sort_key)
    return suites


def _match_suite(token: str, suites: list[Suite]) -> Suite:
    query = token.casefold()
    exact_matches = [
        suite
        for suite in suites
        if query
        in {
            suite.name.casefold(),
            suite.display_name.casefold(),
            suite.suite_dir.parent.name.casefold(),
            *(alias.casefold() for alias in suite.aliases),
        }
    ]
    if len(exact_matches) == 1:
        return exact_matches[0]
    if len(exact_matches) > 1:
        raise ValueError(f"Mehrdeutige Suite-Auswahl fuer '{token}'.")

    partial_matches = [
        suite
        for suite in suites
        if query in suite.name.casefold()
        or query in suite.display_name.casefold()
        or any(query in alias.casefold() for alias in suite.aliases)
    ]
    if len(partial_matches) == 1:
        return partial_matches[0]
    if not partial_matches:
        raise ValueError(f"Unbekannte Suite: {token}")
    raise ValueError(f"Mehrdeutige Suite-Auswahl fuer '{token}'.")


def _selected_suites(args: argparse.Namespace, suites: list[Suite]) -> list[Suite]:
    if args.list:
        return suites
    if args.all:
        return suites
    if not args.modules:
        raise ValueError("Bitte --all, --module <name> oder --list angeben.")

    selected: list[Suite] = []
    seen: set[Path] = set()
    for token in args.modules:
        suite = _match_suite(token, suites)
        if suite.suite_dir not in seen:
            selected.append(suite)
            seen.add(suite.suite_dir)
    return selected


def _invoke(script_path: Path) -> int:
    completed = subprocess.run(["cmd.exe", "/c", "call", str(script_path)], cwd=script_path.parent)
    return completed.returncode


def _warn_if_legacy_root_venv_exists(suite: Suite) -> None:
    legacy_venv = suite.suite_dir.parent / ".venv"
    if not legacy_venv.exists():
        return
    print(
        f"[WARN] Ignoriere Altlast-venv ausserhalb der Suite: {legacy_venv} "
        f"(verwende {suite.suite_dir / '.venv'})",
        file=sys.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the unified Vision Pipeline dev test suites.")
    parser.add_argument("--list", action="store_true", help="List all discovered dev test suites.")
    parser.add_argument("--module", action="append", dest="modules", help="Run only the named suite. Can be repeated.")
    parser.add_argument("--all", action="store_true", help="Run all discovered suites.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--bootstrap-only", action="store_true", help="Only build the suite-local environments.")
    mode.add_argument("--run-only", action="store_true", help="Only execute the suite tests.")
    args = parser.parse_args(argv)

    suites = _discover_suites()
    selected = _selected_suites(args, suites)

    if args.list:
        for suite in selected:
            print(f"{suite.name}\t{suite.kind}\t{suite.suite_dir}")
        return 0

    for suite in selected:
        print(f"[SUITE] {suite.display_name}")
        _warn_if_legacy_root_venv_exists(suite)
        if not args.run_only:
            if not suite.bootstrap_script.exists():
                raise FileNotFoundError(f"Bootstrap-Skript fehlt: {suite.bootstrap_script}")
            if _invoke(suite.bootstrap_script) != 0:
                print(f"[FAIL] Bootstrap fehlgeschlagen: {suite.display_name}", file=sys.stderr)
                return 1
        if not args.bootstrap_only:
            if not suite.run_script.exists():
                raise FileNotFoundError(f"Run-Skript fehlt: {suite.run_script}")
            if _invoke(suite.run_script) != 0:
                print(f"[FAIL] Testlauf fehlgeschlagen: {suite.display_name}", file=sys.stderr)
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
