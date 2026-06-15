from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.paths import stable_hash
from semantic_control_kernel.types.batches import PipelineInputFile, PipelineRunTarget
from semantic_control_kernel.validation.batch_validation import validate_pipeline_batch_manifest


def scan_input_files(target: PipelineRunTarget) -> list[PipelineInputFile]:
    artifact_root = Path(target.artifact_root_path).resolve(strict=False)
    input_root = Path(target.input_path).resolve(strict=False)
    if not input_root.is_dir():
        return []
    files: list[PipelineInputFile] = []
    for path in sorted(input_root.rglob("*"), key=lambda item: item.as_posix().casefold()):
        if not path.is_file():
            continue
        resolved = path.resolve(strict=False)
        content_hash = _content_hash(resolved)
        input_relative_path = _artifact_relpath(resolved, artifact_root)
        input_under_root = _input_relpath(resolved, input_root)
        files.append(
            PipelineInputFile(
                input_file_id="inp_" + stable_hash(f"{input_relative_path}:{content_hash}:{path.stat().st_size}")[:24],
                input_relative_path=input_relative_path,
                original_ref=f"Documents/originals/{input_under_root}",
                content_hash=content_hash,
                size_bytes=path.stat().st_size,
                source_kind=_source_kind(path),
                ingest_route="manual_pipeline_run",
                pre_run_location=input_relative_path,
                post_run_original_location=f"Documents/originals/{input_under_root}",
            )
        )
    return files


def input_set_hash(files: list[PipelineInputFile]) -> str:
    seed = [
        {
            "content_hash": item.content_hash,
            "input_relative_path": item.input_relative_path,
            "size_bytes": item.size_bytes,
        }
        for item in files
    ]
    return "sha256:" + stable_hash(json.dumps(seed, sort_keys=True, separators=(",", ":"), ensure_ascii=True))


def count_error_case_sources(artifact_root: str | Path) -> int:
    error_root = Path(artifact_root) / "Error Cases"
    if not error_root.is_dir():
        return 0
    return len(_error_case_original_files(error_root))


def _error_case_original_files(error_root: Path) -> list[Path]:
    originals_dirs = [path for path in error_root.rglob("originals") if path.is_dir()]
    files: set[Path] = set()
    for originals_dir in originals_dirs:
        for path in originals_dir.rglob("*"):
            if path.is_file():
                files.add(path)
    return sorted(files)


def latest_final_batch_manifest(artifact_root: str | Path) -> dict[str, Any] | None:
    root = Path(artifact_root)
    batch_root = root / "Documents" / "logs" / "pipeline_batches"
    if not batch_root.is_dir():
        return None
    manifests = sorted(
        batch_root.glob("pbt_*/pipeline_batch_manifest.json"),
        key=lambda path: path.stat().st_mtime_ns if path.exists() else 0,
        reverse=True,
    )
    for path in manifests:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                continue
            validate_pipeline_batch_manifest(payload)
        except Exception:
            continue
        return payload
    return None


def manifest_original_refs_exist(target: PipelineRunTarget, manifest: Mapping[str, Any]) -> bool:
    input_files = manifest.get("input_files")
    if not isinstance(input_files, list):
        return False
    for item in input_files:
        if not isinstance(item, Mapping):
            return False
        original_ref = str(item.get("original_ref") or "").strip()
        if not original_ref:
            return False
        path = Path(original_ref)
        if not path.is_absolute():
            path = Path(target.artifact_root_path) / path
        if not path.exists():
            return False
    return True


def _content_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _artifact_relpath(path: Path, artifact_root: Path) -> str:
    try:
        return path.relative_to(artifact_root).as_posix()
    except ValueError:
        return str(path)


def _input_relpath(path: Path, input_root: Path) -> str:
    try:
        return path.relative_to(input_root).as_posix()
    except ValueError:
        return path.name


def _source_kind(path: Path) -> str:
    suffix = path.suffix.casefold()
    if suffix == ".pdf":
        return "pdf"
    if suffix in {".doc", ".docx", ".odt", ".rtf"}:
        return "document"
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
        return "image"
    if suffix in {".txt", ".md", ".csv", ".json", ".xml"}:
        return "text"
    return "document"
