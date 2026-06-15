"""Runtime and startup report helpers for the bundled Edit Suite."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any

from ..registry import discover_registry
from . import adapter, workflow


def _join_relative(root: Path, value: str) -> Path:
    parts = [part for part in str(value).replace("\\", "/").split("/") if part and part != "."]
    return root.joinpath(*parts).resolve()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _runtime_manifest(module_root: Path) -> dict[str, Any]:
    return adapter.load_json_object(module_root / "runtime" / "runtime-manifest.json", label="runtime-manifest.json")


def collect_runtime_report(root: str | Path | None = None) -> dict[str, Any]:
    module_root = workflow.module_root(root)
    runtime_root = (module_root / "runtime" / "python").resolve()
    report = {
        "ok": False,
        "root_dir": str(module_root),
        "runtime_root": str(runtime_root),
        "missing_files": [],
        "violations": [],
        "python": {"path": str(Path(sys.executable).resolve()), "version": sys.version.split()[0], "candidates": []},
        "provenance": {"encodings": "", "tkinter": "", "customtkinter": ""},
        "error": "",
    }
    try:
        manifest = _runtime_manifest(module_root)
    except Exception as exc:
        report["error"] = str(exc)
        return report
    candidates = [_join_relative(module_root, str(value)) for value in manifest["runtime_candidates"]["python"]]
    required_files = [_join_relative(module_root, str(value)) for value in manifest["required_files"]]
    report["python"]["candidates"] = [str(path) for path in candidates]
    report["missing_files"] = [str(path) for path in required_files if not path.exists()]
    if report["missing_files"]:
        report["error"] = "Bundled runtime is incomplete."
        return report
    try:
        customtkinter = importlib.import_module("customtkinter")
        encodings = importlib.import_module("encodings")
        tkinter = importlib.import_module("tkinter")
    except Exception as exc:
        report["error"] = f"Bundled Python starts, but runtime imports are missing: {exc}"
        return report
    report["provenance"]["encodings"] = str(Path(encodings.__file__).resolve())
    report["provenance"]["tkinter"] = str(Path(tkinter.__file__).resolve())
    report["provenance"]["customtkinter"] = str(Path(customtkinter.__file__).resolve())
    for label, candidate in (
        ("python.path", Path(report["python"]["path"])),
        ("provenance.encodings", Path(report["provenance"]["encodings"])),
        ("provenance.tkinter", Path(report["provenance"]["tkinter"])),
        ("provenance.customtkinter", Path(report["provenance"]["customtkinter"])),
    ):
        if not _is_within(candidate, runtime_root):
            report["violations"].append(f"{label} is outside the bundled runtime: {candidate}")
    if Path(report["python"]["path"]).resolve() not in {path.resolve() for path in candidates if path.exists()}:
        report["violations"].append("python.exe does not match runtime-manifest.json.")
    if report["violations"]:
        report["error"] = "Runtime provenance is not portable."
        return report
    report["ok"] = True
    return report


def collect_startup_report(root: str | Path | None = None) -> dict[str, Any]:
    module_root = workflow.module_root(root)
    runtime = collect_runtime_report(module_root)
    suite = {"ok": False, "state_root": "", "module_count": 0, "source": "live", "error": "", "modules": []}
    if runtime["ok"]:
        try:
            context = workflow.ensure_startup_prerequisites(module_root)
            snapshot = discover_registry(context.pipeline_root, state_root=context.state_root)
        except Exception as exc:
            suite["error"] = str(exc)
        else:
            suite["ok"] = True
            suite["state_root"] = str(context.state_root)
            suite["module_count"] = len(snapshot.entries)
            suite["source"] = snapshot.source
            suite["modules"] = [entry.to_dict() for entry in snapshot.entries]
    return {"ok": bool(runtime["ok"] and suite["ok"]), "root_dir": str(module_root), "runtime": runtime, "suite": suite, "error": suite["error"] or runtime["error"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit runtime or startup health for the Edit Suite bundle.")
    parser.add_argument("--root", default="", help="Optional module root. Defaults to the current package root.")
    parser.add_argument("--mode", choices=("runtime", "startup"), default="runtime")
    args = parser.parse_args(argv)
    report = collect_startup_report(args.root) if args.mode == "startup" else collect_runtime_report(args.root)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
