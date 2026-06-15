from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from llm_interpreter.edit_contract.summary import build_module_summary


def test_build_module_summary_describes_runtime_limits_prompts_and_boundaries() -> None:
    summary = build_module_summary()

    assert summary.startswith("INTERPRETER HELP")
    assert "How To Read This Slot" in summary
    assert "Runtime Policy Guide" in summary
    assert "`LOG_LEVEL` controls the saved local log verbosity for future runs." in summary
    assert "Execution Limits Guide" in summary
    assert "`OPENAI_API_BASE_URL` is the advanced saved endpoint override." in summary
    assert "Output Contract Guide" in summary
    assert "Auth, model choice, `MAX_OUTPUT_TOKENS`, and thinking remain orchestrator-owned." in summary

