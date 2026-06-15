from __future__ import annotations

from pathlib import Path


def image_dir(root: Path, payload: dict) -> Path:
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    file_name = str(source.get("file_name") or Path(str(source.get("file_path") or "")).name)
    hash_text = str(source.get("content_hash") or "").removeprefix("sha256:")
    return root / f"{file_name.replace(' ', '_')}.{hash_text[:8]}"


def write_page_image(root: Path, payload: dict, blob: bytes, *, page: int = 1) -> None:
    target_dir = image_dir(root, payload)
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / f"page_{page:03d}.jpg").write_bytes(blob)


def set_source_hash(payload: dict, content_hash: str) -> dict:
    updated = dict(payload)
    updated["source"] = dict(payload.get("source") or {})
    updated["source"]["content_hash"] = content_hash
    return updated
