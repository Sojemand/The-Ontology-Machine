from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _copy_module(tmp_path: Path) -> Path:
    module_root = tmp_path / "normalizer_module"
    shutil.copytree(PROJECT_ROOT / "normalizer_vision", module_root / "normalizer_vision")
    shutil.copytree(PROJECT_ROOT / "config", module_root / "config")
    shutil.copytree(PROJECT_ROOT / "vision_pipeline_shared", module_root / "vision_pipeline_shared")
    shutil.copy2(PROJECT_ROOT / "module-manifest.json", module_root / "module-manifest.json")
    return module_root


def _write_sitecustomize(module_root: Path) -> None:
    (module_root / "sitecustomize.py").write_text(
        """
import normalizer_vision.normalizer as normalizer_mod
import normalizer_vision.orchestrator_contract.workflow as contract_workflow


class _FakeProvider:
    provider_name = "standalone-smoke"

    def generate(self, messages, schema=None, max_output_tokens=None, thinking_effort=None):
        return {"accepted": True}


class _FakeNormalizer:
    def _build_provider(self):
        return _FakeProvider()


normalizer_mod.DocumentNormalizer.from_project = classmethod(
    lambda cls, root, runtime_settings=None: _FakeNormalizer()
)
contract_workflow.create_provider = lambda config: _FakeProvider()
""".strip()
        + "\n",
        encoding="utf-8",
    )


def _invoke_contract(module_root: Path, *, contract_module: str, payload: dict) -> dict:
    request_path = module_root / "request.json"
    response_path = module_root / "response.json"
    request_path.write_text(json.dumps(payload), encoding="utf-8")
    env = dict(os.environ)
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(module_root) if not existing_pythonpath else os.pathsep.join((str(module_root), existing_pythonpath))
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            contract_module,
            "--request",
            str(request_path),
            "--response",
            str(response_path),
        ],
        cwd=module_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return json.loads(response_path.read_text(encoding="utf-8"))


def test_standalone_copy_supports_normalizer_orchestrator_contract(tmp_path: Path) -> None:
    module_root = _copy_module(tmp_path)
    _write_sitecustomize(module_root)

    healthcheck = _invoke_contract(
        module_root,
        contract_module="normalizer_vision.orchestrator_contract",
        payload={
            "action": "healthcheck",
            "runtime_settings": {"model": "gpt-5.4-mini", "max_output_tokens": 15000},
        },
    )
    publish_path = tmp_path / "semantic_release.default.json"
    published = _invoke_contract(
        module_root,
        contract_module="normalizer_vision.orchestrator_contract",
        payload={"action": "publish_semantic_release", "output_path": str(publish_path)},
    )
    catalog = _invoke_contract(
        module_root,
        contract_module="normalizer_vision.orchestrator_contract",
        payload={"action": "build_projection_catalog"},
    )

    assert healthcheck["status"] == "OK"
    assert healthcheck["healthy"] is True
    assert published["status"] == "OK"
    assert publish_path.exists()
    assert published["release_id"]
    assert catalog["status"] == "OK"
    assert catalog["projection_catalog"]["projections"]


def test_standalone_copy_supports_normalizer_edit_contract_bundle_actions(tmp_path: Path) -> None:
    module_root = _copy_module(tmp_path)

    described = _invoke_contract(
        module_root,
        contract_module="normalizer_vision.edit_contract",
        payload={"action": "describe_surfaces"},
    )
    bundled = _invoke_contract(
        module_root,
        contract_module="normalizer_vision.edit_contract",
        payload={"action": "read_bundle"},
    )

    assert described["status"] == "ok"
    assert bundled["status"] == "ok"
    assert [item["surface_id"] for item in bundled["surfaces"]] == [item["surface_id"] for item in described["surfaces"]]
    assert all(isinstance(item.get("value"), dict) for item in bundled["surfaces"])
