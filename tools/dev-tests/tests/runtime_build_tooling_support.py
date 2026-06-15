from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


PIPELINE_ROOT = Path(__file__).resolve().parents[3]
TOOLS_ROOT = Path(__file__).resolve().parents[2]
NORMALIZER_ROOT = PIPELINE_ROOT / "04 - Normalizer"
OPTIMIZER_ROOT = PIPELINE_ROOT / "01 - Optimizer"
INTERPRETER_ROOT = PIPELINE_ROOT / "02 - Interpreter"
VALIDATOR_ROOT = PIPELINE_ROOT / "03 - Validator"
CLIENT_FRONTEND_ROOT = PIPELINE_ROOT / "Client Frontend"
OPTIMIZER_BUILD_SCRIPT_PATH = OPTIMIZER_ROOT / "tools" / "build-runtime.bat"
OPTIMIZER_BUILD_PS1_PATH = OPTIMIZER_ROOT / "tools" / "build-runtime.ps1"
INTERPRETER_BUILD_SCRIPT_PATH = INTERPRETER_ROOT / "tools" / "build-runtime.bat"
INTERPRETER_BUILD_PS1_PATH = INTERPRETER_ROOT / "tools" / "build-runtime.ps1"
INTERPRETER_BUILD_HOOK_PATH = INTERPRETER_ROOT / "tools" / "build-runtime.py"
CLIENT_FRONTEND_BUILD_SCRIPT_PATH = CLIENT_FRONTEND_ROOT / "build-runtime.bat"
OPTIMIZER_REQUIREMENTS_PATH = OPTIMIZER_ROOT / "requirements.txt"
INTERPRETER_REQUIREMENTS_PATH = INTERPRETER_ROOT / "requirements.txt"


def load_tool_module(name: str, path: Path):
    if str(TOOLS_ROOT) not in sys.path:
        sys.path.insert(0, str(TOOLS_ROOT))
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
