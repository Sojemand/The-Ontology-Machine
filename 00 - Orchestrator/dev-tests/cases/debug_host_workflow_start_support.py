from __future__ import annotations

from pathlib import Path

from orchestrator.debug_host.types import DebugProcessHandle


class ProcessStub:
    def poll(self):
        return None


def fake_launch(captured: dict[str, object]):
    def launch(spec, payload, *, request_path, response_path, env_overlay=None, bootstrap_home=None):  # noqa: ANN001
        captured["spec"] = spec
        captured["payload"] = payload
        captured["env_overlay"] = env_overlay
        captured["bootstrap_home"] = bootstrap_home
        return DebugProcessHandle(process=ProcessStub(), request_path=request_path, response_path=response_path)

    return launch


def handle_for_request_response() -> DebugProcessHandle:
    return DebugProcessHandle(
        process=ProcessStub(),
        request_path=Path("request.json"),
        response_path=Path("response.json"),
    )


class ModulesWithRuntimeSettings:
    class _RuntimeSettings:
        def __init__(self, runtime_settings: dict[str, dict[str, object]]):
            self._runtime_settings = runtime_settings

        def runtime_settings_for(self, module_key: str, operation: str = ""):
            del operation
            return self._runtime_settings.get(module_key)

    def __init__(self, runtime_settings: dict[str, dict[str, object]]):
        self._runtime_settings = self._RuntimeSettings(runtime_settings)
