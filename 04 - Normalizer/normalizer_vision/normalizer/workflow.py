"""Workflow stage for normalizer orchestration."""
from __future__ import annotations

import logging
import time as system_time
from collections.abc import Callable
from pathlib import Path

from ..document_io import StructuredDocument, load_structured_document
from ..models.config import NormalizerExecutionConfig, NormalizerProjectConfig
from ..models.results import NormalizationResult
from ..projection_routing import resolve_projection
from ..prompts import PromptBundle, build_messages, get_output_schema
from ..release_runtime import ReleaseRuntime
from ..taxonomy import TaxonomyProfile
from . import document, policy, repository, validation
from .provider_workflow import generate_response_text
from .types import ModelClient, NormalizedEnvelope

logger = logging.getLogger(__name__)


def build_prompt_preview(
    *,
    project_root: Path,
    structured_path: Path,
    config: NormalizerProjectConfig,
    profile: TaxonomyProfile,
    prompt_bundle: PromptBundle,
    release_runtime: ReleaseRuntime | None = None,
) -> tuple[str, str]:
    structured_doc = load_structured_document(structured_path, max_bytes=config.max_structured_bytes)
    selection = resolve_projection(
        project_root=project_root,
        fallback_profile=profile,
        raw_doc=structured_doc.payload,
        hint_mode=config.projection_hint_mode,
        release_runtime=release_runtime,
    )
    messages = build_messages(structured_doc.payload, selection.profile, prompt_bundle)
    return str(messages[0]["content"]), str(messages[1]["content"])


def normalize_document(
    *,
    project_root: Path,
    structured_path: Path,
    normalized_output_path: Path,
    request_output_path: Path | None = None,
    config: NormalizerExecutionConfig,
    profile: TaxonomyProfile,
    prompt_bundle: PromptBundle,
    provider_builder: Callable[[], ModelClient],
    sleep: Callable[[float], None],
    release_runtime: ReleaseRuntime | None = None,
) -> NormalizationResult:
    started = system_time.perf_counter()
    try:
        structured_doc = load_structured_document(structured_path, max_bytes=config.max_structured_bytes)
        envelope = run_normalization(
            project_root=project_root,
            structured_doc=structured_doc,
            config=config,
            profile=profile,
            prompt_bundle=prompt_bundle,
            provider_builder=provider_builder,
            sleep=sleep,
            release_runtime=release_runtime,
            request_output_path=request_output_path,
        )
        target = repository.write_normalized_output(
            normalized_output_path=normalized_output_path,
            normalized=envelope.to_dict(),
        )
        return NormalizationResult(
            input_path=str(structured_path),
            output_path=str(target),
            status="OK",
            needs_review=bool(envelope.processing.get("needs_review", False)),
            duration_ms=_duration_ms(started),
            message="normalized",
            review_reason=str(envelope.processing.get("review_reason") or ""),
        )
    except Exception as exc:
        return NormalizationResult(
            input_path=str(structured_path),
            output_path=None,
            status="ERROR",
            needs_review=True,
            duration_ms=_duration_ms(started),
            message=str(exc),
            review_reason="",
        )


def normalize_batch(
    *,
    project_root: Path,
    structured_dir: Path,
    output_root: Path,
    workers: int | None,
    config: NormalizerExecutionConfig,
    profile: TaxonomyProfile,
    prompt_bundle: PromptBundle,
    provider_builder: Callable[[], ModelClient],
    provider_is_injected: bool,
    thread_pool_factory: Callable[..., Any],
    progress_callback: Callable[[NormalizationResult], None] | None,
    sleep: Callable[[float], None],
    release_runtime: ReleaseRuntime | None = None,
) -> list[NormalizationResult]:
    from . import batch_workflow

    return batch_workflow.normalize_batch(
        project_root=project_root,
        structured_dir=structured_dir,
        output_root=output_root,
        workers=workers,
        config=config,
        profile=profile,
        prompt_bundle=prompt_bundle,
        provider_builder=provider_builder,
        provider_is_injected=provider_is_injected,
        thread_pool_factory=thread_pool_factory,
        progress_callback=progress_callback,
        sleep=sleep,
        release_runtime=release_runtime,
    )


def run_normalization(
    *,
    project_root: Path,
    structured_doc: StructuredDocument,
    config: NormalizerExecutionConfig,
    profile: TaxonomyProfile,
    prompt_bundle: PromptBundle,
    provider_builder: Callable[[], ModelClient],
    sleep: Callable[[float], None],
    release_runtime: ReleaseRuntime | None = None,
    request_output_path: Path | None = None,
) -> NormalizedEnvelope:
    provider = provider_builder()
    selection = resolve_projection(
        project_root=project_root,
        fallback_profile=profile,
        raw_doc=structured_doc.payload,
        hint_mode=config.projection_hint_mode,
        release_runtime=release_runtime,
    )
    messages = build_messages(structured_doc.payload, selection.profile, prompt_bundle)
    schema = get_output_schema(selection.profile) if config.structured_outputs else None
    if request_output_path is not None:
        repository.write_normalizer_request(
            request_output_path=request_output_path,
            structured_path=structured_doc.path,
            config=config,
            provider_name=provider.provider_name,
            projection_selection=selection.to_dict(),
            messages=messages,
            schema=schema,
        )
    response_text = generate_response_text(structured_doc, config, provider, messages, schema, sleep)
    parsed = validation.parse_model_output(policy.strip_code_fences(response_text))
    return document.build_normalized_envelope(
        config=config,
        profile=selection.profile,
        raw_doc=structured_doc.payload,
        parsed=parsed,
        provider_name=provider.provider_name,
        projection_selection=selection,
    )


def _duration_ms(started: float) -> int:
    return int((system_time.perf_counter() - started) * 1000)
