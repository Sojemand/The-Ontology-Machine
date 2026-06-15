from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.policy.runtime_locale import DEFAULT_CONTROL_LOCALE
from semantic_control_kernel.repository.paths import utc_iso
from semantic_control_kernel.workflows.llm_calls.artifacts import LLMArtifactStore
from semantic_control_kernel.workflows.llm_calls.update_state_building.errors import UpdateStateBuilderError
from semantic_control_kernel.workflows.llm_calls.update_state_validation import validate_update_state_artifact

def _source_artifacts(folder: str, analysis_run_id: str, proposal_file: str, *, view: str | None = None) -> dict[str, str]:
    prefix = f"{folder}/{analysis_run_id}"
    payload = {
        "proposal_path": f"{prefix}/{proposal_file}",
        "prompt_snapshot_path": f"{prefix}/prompt.json",
        "llm_response_path": f"{prefix}/raw.json",
    }
    if view is not None:
        payload["view_path"] = f"{prefix}/{view}"
    return payload


def _validation_stamp() -> dict[str, str]:
    return {
        "validated_at": utc_iso(),
        "validator": "semantic_control_kernel",
        "validator_version": "phase8.v1",
        "schema_validation": "passed",
        "source_package_validation": "passed",
    }


def _finalize_update_state(
    state: dict[str, Any],
    artifact_root: str | Path | None,
    folder: str,
    analysis_run_id: str,
    file_name: str,
) -> dict[str, Any]:
    validate_update_state_artifact(state, state["schema_version"])
    if artifact_root is not None:
        store = LLMArtifactStore(artifact_root)
        path = store.artifact_root / folder / analysis_run_id / file_name
        path.parent.mkdir(parents=True, exist_ok=True)
        store.write_json(path, state)
    return state


def _runtime_locale(real_taxonomy_proof: Mapping[str, Any] | None) -> str:
    if real_taxonomy_proof and isinstance(real_taxonomy_proof.get("runtime_locale"), str):
        return str(real_taxonomy_proof["runtime_locale"])
    return DEFAULT_CONTROL_LOCALE


def _mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise UpdateStateBuilderError(f"{key} is required.")
    return value


def _list(payload: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise UpdateStateBuilderError(f"{key} must be a list of objects.")
    return value
