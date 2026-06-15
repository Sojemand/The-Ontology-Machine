from __future__ import annotations

from phase11_adapter_fakes import FakeBatchAdapter, FakeCorpusAdapter, FakeOrchestratorAdapter
from phase11_owner_output_fakes import final_manifest_for, owner_output, owner_output_for_request, with_bad_final_manifest
from phase11_result_fakes import blocked_precondition, missing, ok_result, owner_error
from phase11_runtime_fakes import runtime_for
from phase11_target_fakes import confirmation_for, input_files, target_for

__all__ = [
    "FakeBatchAdapter",
    "FakeCorpusAdapter",
    "FakeOrchestratorAdapter",
    "blocked_precondition",
    "confirmation_for",
    "final_manifest_for",
    "input_files",
    "missing",
    "ok_result",
    "owner_error",
    "owner_output",
    "owner_output_for_request",
    "runtime_for",
    "target_for",
    "with_bad_final_manifest",
]
