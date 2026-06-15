"""Plain request artifact copying for frozen error bundles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import artifact_repository, path_budget, policy, storage_repository

_MIN_MULTI_PAGE_REQUEST_DIR_LENGTH = len("a.12345678.p000.of000")
MULTI_PAGE_REQUEST_RESERVED = _MIN_MULTI_PAGE_REQUEST_DIR_LENGTH + max(
    len(policy.request_file_name("ocr_request")),
    len(policy.request_file_name("interpreter_request")),
    len(policy.request_file_name("normalizer_request")),
) + 2


@dataclass(frozen=True)
class CopiedRequestArtifacts:
    optimizer_ocr_paths: tuple[Path, ...] = ()
    interpreter_paths: tuple[Path, ...] = ()
    normalizer_paths: tuple[Path, ...] = ()

    @property
    def all_paths(self) -> tuple[Path, ...]:
        return self.optimizer_ocr_paths + self.interpreter_paths + self.normalizer_paths

    def __len__(self) -> int:
        return len(self.all_paths)

    def __getitem__(self, index: int) -> Path:
        return self.all_paths[index]


def copy_plain_requests_to_bundle(
    engine: Any,
    record: Any,
    bundle_path: Path,
    *,
    allowed_roots: tuple[Path, ...],
    attr_list: str,
    attr_single: str,
    request_key: str,
    purpose: str,
    page_suffix: str = "",
) -> list[Path]:
    request_paths = list(getattr(record.artifacts, attr_list, []) or [])
    if not request_paths:
        request_source_text = str(getattr(record.artifacts, attr_single, "") or "").strip()
        request_paths = [request_source_text] if request_source_text else []
    published: list[Path] = []
    single_request = len([path for path in request_paths if str(path).strip()]) == 1
    request_name = policy.request_file_name(request_key)
    for request_source_text in request_paths:
        if not str(request_source_text).strip():
            continue
        published.extend(
            _copy_plain_request(
                engine,
                record,
                bundle_path,
                Path(request_source_text),
                allowed_roots=allowed_roots,
                request_name=request_name,
                purpose=purpose,
                single_request=single_request,
                page_suffix=page_suffix,
            )
        )
    return published


def _copy_plain_request(
    engine: Any,
    record: Any,
    bundle_path: Path,
    source: Path,
    *,
    allowed_roots: tuple[Path, ...],
    request_name: str,
    purpose: str,
    single_request: bool,
    page_suffix: str,
) -> list[Path]:
    publication_root = storage_repository.publication_root(bundle_path, "requests")
    relative_output_path = policy.record_relative_output_path(engine, record, purpose=purpose)
    if single_request and page_suffix:
        relative_output_path = relative_output_path.with_name(f"{relative_output_path.name}{page_suffix}")
    request_root = publication_root / path_budget.budgeted_relative_path(
        publication_root,
        relative_output_path,
        reserved=MULTI_PAGE_REQUEST_RESERVED if not single_request else 0,
    )
    if single_request:
        target = request_root / request_name
    else:
        request_dir = request_root / path_budget.budgeted_page_name(
            request_root,
            source.parent.name,
            reserved=len(request_name) + 1,
        )
        target = request_dir / path_budget.budgeted_name(request_dir, source.name)
    artifact_repository.copy_if_exists(engine, source, target, allowed_roots=allowed_roots)
    return [target] if target.exists() else []
