from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = MODULE_ROOT.parent
TOOLS_ROOT = PIPELINE_ROOT / "tools"


def _load_module(module_name: str, path: Path):
    sys.path.insert(0, str(TOOLS_ROOT))
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        assert spec is not None
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.modules.pop(module_name, None)
        sys.path.remove(str(TOOLS_ROOT))


def test_root_runtime_builder_default_order_includes_kernel_after_mcp_server() -> None:
    build_runtimes = _load_module("build_runtimes_for_phase1_test", TOOLS_ROOT / "build-runtimes.py")
    order = list(build_runtimes.DEFAULT_MODULE_DIRS)

    assert "08 - Semantic Control Kernel" in order
    assert order.index("07 - MCP Server") < order.index("08 - Semantic Control Kernel")
    assert order.index("08 - Semantic Control Kernel") < order.index("Client Frontend")


def test_root_dev_test_preferred_order_includes_kernel_after_mcp_server() -> None:
    run_dev_tests = _load_module("run_dev_tests_for_phase1_test", TOOLS_ROOT / "run-dev-tests.py")
    order = list(run_dev_tests.PREFERRED_ORDER)

    assert "08 - Semantic Control Kernel" in order
    assert order.index("07 - MCP Server") < order.index("08 - Semantic Control Kernel")
    assert order.index("08 - Semantic Control Kernel") < order.index("Client Frontend")


def test_root_run_dev_tests_batch_contains_kernel_runtime_candidate() -> None:
    script = (PIPELINE_ROOT / "run-dev-tests.bat").read_text(encoding="utf-8")

    assert '"%~dp008 - Semantic Control Kernel\\runtime\\python\\python.exe"' in script
    assert script.index('"%~dp007 - MCP Server\\runtime\\python\\python.exe"') < script.index(
        '"%~dp008 - Semantic Control Kernel\\runtime\\python\\python.exe"'
    )
    assert script.index('"%~dp008 - Semantic Control Kernel\\runtime\\python\\python.exe"') < script.index(
        '"%~dp000 - Orchestrator\\runtime\\python\\python.exe"'
    )


def test_dev_test_suite_json_is_discoverable_by_required_aliases() -> None:
    run_dev_tests = _load_module("run_dev_tests_discovery_for_phase1_test", TOOLS_ROOT / "run-dev-tests.py")
    suite_payload = json.loads((MODULE_ROOT / "dev-tests" / "suite.json").read_text(encoding="utf-8"))
    suites = run_dev_tests._discover_suites()

    assert suite_payload["name"] == "08 - Semantic Control Kernel"
    assert suite_payload["display_name"] == "08 - Semantic Control Kernel"
    assert suite_payload["kind"] == "python"
    for token in ("08 - Semantic Control Kernel", "semantic-control-kernel", "kernel"):
        suite = run_dev_tests._match_suite(token, suites)
        assert suite.name == "08 - Semantic Control Kernel"
