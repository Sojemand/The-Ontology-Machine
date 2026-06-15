from __future__ import annotations

import importlib
import sys
from pathlib import Path

from semantic_control_kernel.bootstrap.runtime_report_constants import MODULE_KEY
from semantic_control_kernel.bootstrap.runtime_report_paths import is_relative_to


def contract_import_check(module_root: Path, sys_path: list[str]) -> tuple[bool, str]:
    before = side_effect_snapshot(module_root)
    old_path = sys.path[:]
    saved_modules = kernel_modules()
    contract_name = f"{MODULE_KEY}.orchestrator_contract"
    try:
        restore_kernel_modules({})
        sys.path[:] = sys_path
        imported = importlib.import_module(contract_name)
        imported_path = Path(str(getattr(imported, "__file__", ""))).resolve()
        expected_path = (module_root / MODULE_KEY / "orchestrator_contract.py").resolve()
        if imported_path != expected_path:
            return False, f"orchestrator_contract resolves outside module root: {imported_path}"
        imported_siblings = sorted(name for name in sys.modules if name.startswith(MODULE_KEY + ".") and name != contract_name)
        if imported_siblings:
            return False, "orchestrator_contract imported sibling modules: " + ", ".join(imported_siblings)
    except Exception as exc:
        return False, f"orchestrator_contract import failed: {exc}"
    finally:
        sys.path[:] = old_path
        restore_kernel_modules(saved_modules)
    if before != side_effect_snapshot(module_root):
        return False, "orchestrator_contract import created or removed state, runtime, log or support files."
    return True, "orchestrator_contract imports without sibling imports or file side effects."


def side_effect_snapshot(module_root: Path) -> dict[str, set[str]]:
    return {
        str(root.relative_to(module_root)): tree_snapshot(root)
        for root in (
            module_root / "state",
            module_root / "runtime",
            module_root / "logs",
            module_root / "support",
        )
    }


def tree_snapshot(root: Path) -> set[str]:
    if not root.exists():
        return {"<missing>"}
    entries = {"."}
    for path in root.rglob("*"):
        if path.exists():
            entries.add(path.relative_to(root).as_posix())
    return entries


def kernel_modules() -> dict[str, object]:
    prefix = MODULE_KEY + "."
    return {name: module for name, module in sys.modules.items() if name == MODULE_KEY or name.startswith(prefix)}


def restore_kernel_modules(saved_modules: dict[str, object]) -> None:
    prefix = MODULE_KEY + "."
    for name in list(sys.modules):
        if name == MODULE_KEY or name.startswith(prefix):
            sys.modules.pop(name, None)
    sys.modules.update(saved_modules)
