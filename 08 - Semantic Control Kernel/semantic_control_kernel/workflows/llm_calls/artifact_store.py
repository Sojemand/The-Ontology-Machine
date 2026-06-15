from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.atomic_json import atomic_write_text, ensure_directory, stable_json_dumps
from semantic_control_kernel.types.llm_calls import (
    LLMAttemptMetadata,
    LLMFinalError,
    LLMFunctionDefinition,
    LLMProviderResponse,
    LLMValidationReport,
)
from semantic_control_kernel.workflows.llm_calls.artifact_payloads import (
    _payload_for_binding,
    _response_capture_payload,
    _safe_name,
)
from semantic_control_kernel.workflows.llm_calls.artifact_redaction import (
    redact_capture_payload,
    redact_for_support,
)


class LLMArtifactStore:
    def __init__(self, artifact_root: str | Path) -> None:
        self.artifact_root = Path(artifact_root).resolve(strict=False)

    def run_dir(self, definition: LLMFunctionDefinition, analysis_run_id: str) -> Path:
        relative = definition.run_folder_template.format(analysis_run_id=analysis_run_id)
        path = (self.artifact_root / relative).resolve(strict=False)
        _require_under_root(path, self.artifact_root)
        ensure_directory(path)
        return path

    def write_input_artifacts(self, definition: LLMFunctionDefinition, analysis_run_id: str, input_payload: Any) -> dict[str, str]:
        run_dir = self.run_dir(definition, analysis_run_id)
        binding_paths: dict[str, str] = {}
        if definition.llm_function_name == "analyze_samples" and isinstance(input_payload, list):
            for index, sample in enumerate(input_payload):
                sample_id = _safe_name(str(sample.get("sample_id", f"sample_{index + 1}") if isinstance(sample, Mapping) else f"sample_{index + 1}"))
                rel = definition.input_artifact_paths[0].format(sample_id=sample_id)
                self.write_json(run_dir / rel, redact_capture_payload(sample))
            binding_paths["{{kernel_analyze_sample_inputs_json}}"] = self._relative(run_dir / "in")
            return binding_paths
        for index, rel in enumerate(definition.input_artifact_paths):
            if "{sample_id}" in rel:
                continue
            target = run_dir / rel
            binding = definition.prompt_bindings[index] if index < len(definition.prompt_bindings) else None
            binding_payload = _payload_for_binding(binding, input_payload)
            self.write_json(target, redact_capture_payload(binding_payload))
            if binding is not None:
                binding_paths[binding] = self._relative(target)
        return binding_paths

    def attempt_dir(self, definition: LLMFunctionDefinition, analysis_run_id: str, attempt_index: int) -> Path:
        path = self.run_dir(definition, analysis_run_id) / "a" / str(attempt_index)
        ensure_directory(path)
        return path

    def write_attempt_snapshot(self, definition: LLMFunctionDefinition, analysis_run_id: str, attempt_index: int, snapshot: Mapping[str, Any]) -> str:
        path = self.attempt_dir(definition, analysis_run_id, attempt_index) / "prompt.json"
        self.write_json(path, snapshot)
        return self._relative(path)

    def write_attempt_response(
        self,
        definition: LLMFunctionDefinition,
        analysis_run_id: str,
        attempt_index: int,
        response: LLMProviderResponse,
        *,
        parsed_output: Any,
        parse_status: str,
        validation_status: str,
        validation_errors: list[str],
    ) -> str:
        path = self.attempt_dir(definition, analysis_run_id, attempt_index) / "raw.json"
        self.write_json(path, self.build_response_capture(
            definition=definition,
            analysis_run_id=analysis_run_id,
            attempt_index=attempt_index,
            response=response,
            parsed_output=parsed_output,
            parse_status=parse_status,
            validation_status=validation_status,
            validation_errors=validation_errors,
        ))
        return self._relative(path)

    def write_parsed_output(self, definition: LLMFunctionDefinition, analysis_run_id: str, attempt_index: int, parsed_output: Mapping[str, Any]) -> str:
        path = self.attempt_dir(definition, analysis_run_id, attempt_index) / "parsed.json"
        self.write_json(path, parsed_output)
        return self._relative(path)

    def write_validation_report(self, definition: LLMFunctionDefinition, analysis_run_id: str, attempt_index: int, report: LLMValidationReport) -> str:
        path = self.attempt_dir(definition, analysis_run_id, attempt_index) / "val.json"
        self.write_json(path, report.to_dict())
        return self._relative(path)

    def write_attempt_metadata(self, definition: LLMFunctionDefinition, analysis_run_id: str, attempt_index: int, metadata: LLMAttemptMetadata) -> str:
        path = self.attempt_dir(definition, analysis_run_id, attempt_index) / "meta.json"
        self.write_json(path, metadata.to_dict())
        return self._relative(path)

    def write_canonical_output(self, definition: LLMFunctionDefinition, analysis_run_id: str, output: Mapping[str, Any] | str) -> str:
        path = self.run_dir(definition, analysis_run_id) / definition.canonical_output_path
        if isinstance(output, str):
            self.write_text(path, output)
        else:
            self.write_json(path, output)
        return self._relative(path)

    def write_flat_attempt_copies(self, definition: LLMFunctionDefinition, analysis_run_id: str, snapshot: Mapping[str, Any], response_capture: Mapping[str, Any]) -> tuple[str, str]:
        run_dir = self.run_dir(definition, analysis_run_id)
        prompt_path = run_dir / "prompt.json"
        response_path = run_dir / "raw.json"
        self.write_json(prompt_path, snapshot)
        self.write_json(response_path, response_capture)
        return self._relative(prompt_path), self._relative(response_path)

    def build_response_capture(self, *, definition: LLMFunctionDefinition, analysis_run_id: str, attempt_index: int, response: LLMProviderResponse, parsed_output: Any, parse_status: str, validation_status: str, validation_errors: list[str]) -> dict[str, Any]:
        return _response_capture_payload(
            definition=definition,
            analysis_run_id=analysis_run_id,
            attempt_index=attempt_index,
            response=response,
            parsed_output=parsed_output,
            parse_status=parse_status,
            validation_status=validation_status,
            validation_errors=validation_errors,
        )

    def write_support_bundle(self, definition: LLMFunctionDefinition, analysis_run_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        support_dir = self.run_dir(definition, analysis_run_id) / "s"
        ensure_directory(support_dir)
        support_id = f"support_{definition.llm_function_name}_{analysis_run_id}"
        path = support_dir / "bundle.json"
        self.write_json(path, redact_for_support(payload))
        return {"support_bundle_id": support_id, "artifact_path": self._relative(path)}

    def write_final_error(self, definition: LLMFunctionDefinition, analysis_run_id: str, final_error: LLMFinalError) -> str:
        path = self.run_dir(definition, analysis_run_id) / "error.json"
        self.write_json(path, final_error.to_dict())
        return self._relative(path)

    def write_json(self, path: Path, payload: Any) -> None:
        _require_under_root(path.resolve(strict=False), self.artifact_root)
        serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n" if not isinstance(payload, Mapping) else stable_json_dumps(dict(payload))
        atomic_write_text(path, serialized)

    def write_text(self, path: Path, text: str) -> None:
        _require_under_root(path.resolve(strict=False), self.artifact_root)
        atomic_write_text(path, text)

    def _relative(self, path: Path) -> str:
        return path.resolve(strict=False).relative_to(self.artifact_root).as_posix()


def _require_under_root(path: Path, root: Path) -> None:
    try:
        path.relative_to(root.resolve(strict=False))
    except ValueError as exc:
        raise ValueError(f"LLM artifact path escapes artifact root: {path}") from exc
