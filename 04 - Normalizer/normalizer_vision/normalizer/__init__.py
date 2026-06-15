"""Path-stable surface for the Normalizer Vision workflow."""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ..assets import (
    build_local_release_runtime,
    list_local_profiles,
    load_local_profile,
    prompt_bundle_path,
    prompt_overrides_path,
)
from ..models import RUNTIME_SETTINGS_REQUIRED_MESSAGE
from ..models.config import (
    NormalizerProjectConfig,
    NormalizerRuntimeSettings,
    load_config,
)
from ..prompts import PromptBundle, load_prompt_bundle
from ..providers import create_provider
from ..release_runtime import ReleaseRuntime, build_release_runtime
from ..taxonomy import TaxonomyProfile
from . import policy, validation, workflow
from .types import ModelClient


class DocumentNormalizer:
    @classmethod
    def from_project(
        cls,
        project_root: Path,
        *,
        config_path: Path | None = None,
        runtime_settings: NormalizerRuntimeSettings | None = None,
        provider: ModelClient | None = None,
        semantic_release: dict[str, object] | None = None,
    ) -> "DocumentNormalizer":
        project_config = load_config(project_root, config_path)
        return cls(
            project_root,
            project_config=project_config,
            runtime_settings=runtime_settings,
            provider=provider,
            semantic_release=semantic_release,
        )

    def __init__(
        self,
        project_root: Path,
        project_config: NormalizerProjectConfig | None = None,
        runtime_settings: NormalizerRuntimeSettings | None = None,
        provider: ModelClient | None = None,
        prompt_bundle: PromptBundle | None = None,
        profile: TaxonomyProfile | None = None,
        semantic_release: dict[str, object] | None = None,
    ) -> None:
        self.project_root = project_root
        self.project_config = project_config or load_config(project_root)
        self.config = self.project_config
        self.runtime_settings = runtime_settings
        self._provider = provider
        self._release_runtime = (
            build_release_runtime(
                semantic_release,
                preferred_profile_id=self.project_config.taxonomy_profile_id,
            )
            if semantic_release is not None
            else None
        )
        self._source_release_runtime: ReleaseRuntime | None = None
        self._prompt_bundle = prompt_bundle or load_prompt_bundle(
            prompt_bundle_path(project_root),
            prompt_overrides_path(project_root),
        )
        self._profile = profile or self._load_profile()

    def _load_profile(self) -> TaxonomyProfile:
        if self._release_runtime is not None:
            return self._release_runtime.fallback_profile
        configured_profile_id = self.project_config.taxonomy_profile_id.strip()
        try:
            self._source_release_runtime = build_local_release_runtime(
                self.project_root,
                preferred_profile_id=configured_profile_id,
            )
            return self._source_release_runtime.fallback_profile
        except ValueError:
            self._source_release_runtime = None
        if configured_profile_id:
            try:
                return load_local_profile(self.project_root, configured_profile_id)
            except ValueError:
                pass
        local_profiles = list_local_profiles(self.project_root)
        if not local_profiles:
            raise ValueError("Kein lokales Taxonomie-Profil verfuegbar. Aktiviere einen Semantic Release.")
        return load_local_profile(self.project_root, local_profiles[0].projection_id)

    def _projection_runtime(self) -> ReleaseRuntime | None:
        return self._release_runtime or self._source_release_runtime

    @property
    def profile(self) -> TaxonomyProfile:
        return self._profile

    def _build_provider(self) -> ModelClient:
        if self._provider is not None:
            return self._provider
        return create_provider(self.execution_config)

    def test_connection(self) -> bool:
        self.execution_config
        return self._build_provider().is_available()

    def build_prompt_preview(self, structured_path: Path) -> tuple[str, str]:
        return workflow.build_prompt_preview(
            project_root=self.project_root,
            structured_path=structured_path,
            config=self.project_config,
            profile=self._profile,
            prompt_bundle=self._prompt_bundle,
            release_runtime=self._projection_runtime(),
        )

    def normalize(
        self,
        structured_path: Path,
        normalized_output_path: Path,
        *,
        request_output_path: Path | None = None,
    ):
        execution_config = self.execution_config
        return workflow.normalize_document(
            project_root=self.project_root,
            structured_path=structured_path,
            normalized_output_path=normalized_output_path,
            request_output_path=request_output_path,
            config=execution_config,
            profile=self._profile,
            prompt_bundle=self._prompt_bundle,
            provider_builder=self._build_provider,
            sleep=time.sleep,
            release_runtime=self._projection_runtime(),
        )

    def normalize_batch(
        self,
        structured_dir: Path,
        output_root: Path,
        workers: int | None = None,
        progress_callback=None,
    ):
        execution_config = self.execution_config
        return workflow.normalize_batch(
            project_root=self.project_root,
            structured_dir=structured_dir,
            output_root=output_root,
            workers=workers,
            config=execution_config,
            profile=self._profile,
            prompt_bundle=self._prompt_bundle,
            provider_builder=self._build_provider,
            provider_is_injected=self._provider is not None,
            thread_pool_factory=ThreadPoolExecutor,
            progress_callback=progress_callback,
            sleep=time.sleep,
            release_runtime=self._projection_runtime(),
        )

    @staticmethod
    def _parse_model_output(response_text: str):
        return validation.load_model_output_object(policy.strip_code_fences(response_text))

    @property
    def execution_config(self):
        runtime_settings = self.runtime_settings
        if runtime_settings is None:
            raise RuntimeError(RUNTIME_SETTINGS_REQUIRED_MESSAGE)
        return self.project_config.build_execution_config(runtime_settings)


__all__ = ["DocumentNormalizer", "ModelClient", "ThreadPoolExecutor", "time"]
