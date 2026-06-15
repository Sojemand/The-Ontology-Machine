"""OOXML package path helpers for the docx-python extractor."""
from __future__ import annotations

from pathlib import PurePosixPath


def relationship_part_name(part_name: str) -> str:
    path = PurePosixPath(part_name)
    return str(path.parent / "_rels" / f"{path.name}.rels")


def resolve_part_target(part_name: str, target: str) -> str:
    target_path = PurePosixPath(target.replace("\\", "/"))
    if target.startswith("/"):
        combined = target_path
    else:
        combined = PurePosixPath(part_name).parent / target_path

    normalized_parts: list[str] = []
    for item in combined.parts:
        if item in {"", "."}:
            continue
        if item == "..":
            if normalized_parts:
                normalized_parts.pop()
            continue
        normalized_parts.append(item)
    return "/".join(normalized_parts)
