"""Runtime provenance report for the bundled Corpus Builder runtime."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any

from .policy import package_module_root


def _module_root(root: str | Path | None = None) -> Path:
    return Path(root or package_module_root()).resolve()


def _join_relative(root: Path, value: str) -> Path:
    parts = [part for part in str(value).replace("\\", "/").split("/") if part and part != "."]
    return root.joinpath(*parts).resolve()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _load_runtime_manifest(module_root: Path) -> dict[str, Any]:
    manifest_path = module_root / "runtime" / "runtime-manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("runtime-manifest.json muss ein JSON-Objekt sein.")
    return payload


def _load_module_manifest(module_root: Path) -> dict[str, Any]:
    manifest_path = module_root / "module-manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("module-manifest.json muss ein JSON-Objekt sein.")
    return payload


def _collect_contract_report(module_root: Path) -> dict[str, Any]:
    manifest = _load_module_manifest(module_root)
    contract_module = str(manifest.get("contract_module") or "").strip()
    if not contract_module:
        raise ValueError("module-manifest.json enthaelt kein contract_module.")
    raw_actions = manifest.get("actions", [])
    if not isinstance(raw_actions, list):
        raise ValueError("module-manifest.json actions muss eine Liste sein.")
    manifest_actions = [str(item) for item in raw_actions if str(item).strip()]
    action_module = importlib.import_module(f"{contract_module}.action_names")
    dispatch_module = importlib.import_module(f"{contract_module}.workflow_dispatch")
    validation_module = importlib.import_module(f"{contract_module}.validation")

    code_actions = [str(item) for item in getattr(action_module, "ACTION_NAMES")]
    suite_handlers = getattr(dispatch_module, "_SUITE_HANDLERS", {})
    direct_action_names = (
        "LOAD_DOCUMENT_ACTION",
        "ACTIVATE_SEMANTIC_RELEASE_ACTION",
        "GENERATE_EMBEDDINGS_ACTION",
        "HEALTHCHECK_ACTION",
        "SCAN_DEBUG_INPUT_ACTION",
        "DEBUG_RUN_ACTION",
    )
    direct_actions = {str(getattr(action_module, name)) for name in direct_action_names}
    dispatch_actions = set(suite_handlers) | direct_actions
    parser_names = [
        "parse_load_document_command_fn",
        "parse_activate_semantic_release_command_fn",
        "parse_generate_embeddings_command_fn",
        "parse_healthcheck_command_fn",
        "parse_scan_debug_input_command_fn",
        "parse_debug_run_command_fn",
    ]
    parser_names.extend(str(parser_name) for parser_name, _handler in suite_handlers.values())
    missing_parsers = [
        name[:-3] if name.endswith("_fn") else name
        for name in parser_names
        if not hasattr(validation_module, name[:-3] if name.endswith("_fn") else name)
    ]
    invalid_suite_handlers = [
        action
        for action, value in suite_handlers.items()
        if not isinstance(value, tuple) or len(value) != 2 or not callable(value[1])
    ]
    violations = []
    if manifest_actions != code_actions:
        violations.append("module-manifest.json actions stimmen nicht mit ACTION_NAMES ueberein.")
    missing_dispatch_actions = [action for action in code_actions if action not in dispatch_actions]
    extra_dispatch_actions = sorted(action for action in dispatch_actions if action not in set(code_actions))
    if missing_dispatch_actions:
        violations.append(f"Dispatch-Routen fehlen fuer Actions: {missing_dispatch_actions}")
    if extra_dispatch_actions:
        violations.append(f"Dispatch-Routen ohne ACTION_NAMES-Eintrag: {extra_dispatch_actions}")
    if missing_parsers:
        violations.append(f"Parser fehlen fuer Dispatch-Routen: {missing_parsers}")
    if invalid_suite_handlers:
        violations.append(f"Suite-Handler sind ungueltig: {invalid_suite_handlers}")
    return {
        "contract_module": contract_module,
        "manifest_action_count": len(manifest_actions),
        "code_action_count": len(code_actions),
        "dispatch_action_count": len(dispatch_actions),
        "parser_count": len(parser_names),
        "missing_dispatch_actions": missing_dispatch_actions,
        "extra_dispatch_actions": extra_dispatch_actions,
        "missing_parsers": missing_parsers,
        "invalid_suite_handlers": invalid_suite_handlers,
        "violations": violations,
    }


def collect_runtime_report(root: str | Path | None = None) -> dict[str, Any]:
    module_root = _module_root(root)
    runtime_root = (module_root / "runtime" / "python").resolve()
    report = {
        "ok": False,
        "root_dir": str(module_root),
        "manifest_path": str(module_root / "runtime" / "runtime-manifest.json"),
        "runtime_root": str(runtime_root),
        "missing_files": [],
        "violations": [],
        "python": {
            "path": str(Path(sys.executable).resolve()),
            "version": sys.version.split()[0],
            "base_prefix": str(Path(sys.base_prefix).resolve()),
            "candidates": [],
        },
        "provenance": {
            "encodings": "",
            "sqlite3": "",
        },
        "contract": {},
        "error": "",
    }
    try:
        manifest = _load_runtime_manifest(module_root)
    except Exception as exc:  # pragma: no cover - defensive
        report["error"] = str(exc)
        return report

    raw_candidates = manifest.get("runtime_candidates", {}).get("python", [])
    if not isinstance(raw_candidates, list):
        report["error"] = "runtime-manifest.json enthaelt keine gueltigen Python-Kandidaten."
        return report
    candidates = [_join_relative(module_root, str(value)) for value in raw_candidates if str(value).strip()]
    report["python"]["candidates"] = [str(path) for path in candidates]

    raw_required = manifest.get("required_files", [])
    if not isinstance(raw_required, list):
        report["error"] = "runtime-manifest.json enthaelt keine gueltige required_files-Liste."
        return report
    required_files = [_join_relative(module_root, str(value)) for value in raw_required if str(value).strip()]
    report["missing_files"] = [str(path) for path in required_files if not path.exists()]
    if report["missing_files"]:
        report["error"] = "Gebuendelte Runtime ist unvollstaendig."
        return report

    try:
        encodings = importlib.import_module("encodings")
        sqlite3 = importlib.import_module("sqlite3")
    except Exception as exc:  # pragma: no cover - defensive
        report["error"] = f"Bundled Python startet, aber Runtime-Imports fehlen: {exc}"
        return report

    report["provenance"]["encodings"] = str(Path(encodings.__file__).resolve())
    report["provenance"]["sqlite3"] = str(Path(sqlite3.__file__).resolve())

    executable = Path(report["python"]["path"])
    base_prefix = Path(report["python"]["base_prefix"])
    if candidates and executable.resolve() not in {path.resolve() for path in candidates if path.exists()}:
        report["violations"].append(f"python.exe stimmt nicht mit runtime-manifest.json ueberein: {executable}")
    for label, candidate in (
        ("python.path", executable),
        ("python.base_prefix", base_prefix),
        ("provenance.encodings", Path(report["provenance"]["encodings"])),
        ("provenance.sqlite3", Path(report["provenance"]["sqlite3"])),
    ):
        if not _is_within(candidate, runtime_root):
            report["violations"].append(f"{label} liegt ausserhalb der gebuendelten Runtime: {candidate}")

    expected_version = str(manifest.get("python_version", "")).strip()
    if expected_version and not str(report["python"]["version"]).startswith(expected_version):
        report["violations"].append(
            f"Unerwartete Python-Version: {report['python']['version']} (erwartet {expected_version}.x)"
        )

    try:
        contract_report = _collect_contract_report(module_root)
    except Exception as exc:  # pragma: no cover - defensive
        report["error"] = f"Runtime-Contract kann nicht geladen werden: {exc}"
        return report
    report["contract"] = contract_report
    report["violations"].extend(contract_report["violations"])

    if report["violations"]:
        report["error"] = "Runtime-Provenance oder Contract-Surface ist nicht portable."
        return report

    report["ok"] = True
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit runtime provenance for the bundled Corpus Builder runtime.")
    parser.add_argument("--root", default="", help="Optional module root. Defaults to the current package root.")
    args = parser.parse_args(argv)
    report = collect_runtime_report(args.root)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
