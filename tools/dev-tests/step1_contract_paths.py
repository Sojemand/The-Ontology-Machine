from __future__ import annotations

import importlib.util
import sys
from importlib import import_module
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parents[2]
INTERPRETER_ROOT = PIPELINE_ROOT / "02 - Interpreter"
NORMALIZER_ROOT = PIPELINE_ROOT / "04 - Normalizer"
CORPUS_ROOT = PIPELINE_ROOT / "05 - Corpus Builder"
INTERPRETER_DEV_TESTS_TESTS_ROOT = INTERPRETER_ROOT / "dev-tests" / "tests"
NORMALIZER_DEV_TESTS_ROOT = NORMALIZER_ROOT / "dev-tests"
BASELINE_HELPER_PATH = NORMALIZER_ROOT / "dev-tests" / "tests" / "fixtures" / "taxonomy_refactor_baseline.py"
INTERPRETER_SAMPLE_DATA_PATH = INTERPRETER_ROOT / "dev-tests" / "tests" / "support" / "sample_data.py"

for module_root in (INTERPRETER_DEV_TESTS_TESTS_ROOT, INTERPRETER_ROOT, NORMALIZER_ROOT, NORMALIZER_DEV_TESTS_ROOT, CORPUS_ROOT):
    if str(module_root) not in sys.path:
        sys.path.insert(0, str(module_root))


def load_path_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Modul konnte nicht geladen werden: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASELINE = load_path_module("taxonomy_refactor_step1_baseline", BASELINE_HELPER_PATH)
SAMPLE_DATA = import_module("support.sample_data")
