"""Embedded image reference discovery for DOCX story parts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
import re
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from .ooxml_paths import relationship_part_name, resolve_part_target

_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_NS = {"rel": _REL_NS}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp", ".gif"}


@dataclass(frozen=True)
class EmbeddedImageReference:
    image_name: str
    image_stem: str
    story_part_name: str
    story_part_kind: str


def embedded_image_part_names(archive: ZipFile) -> list[str]:
    return sorted(
        name
        for name in archive.namelist()
        if name.startswith("word/media/") and PurePosixPath(name).suffix.lower() in IMAGE_SUFFIXES
    )


def embedded_image_references(archive: ZipFile, story_parts: list[Any] | tuple[Any, ...]) -> list[EmbeddedImageReference]:
    archive_names = set(archive.namelist())
    references: dict[str, EmbeddedImageReference] = {}

    for story_part in story_parts:
        rels_name = relationship_part_name(story_part.name)
        if rels_name not in archive_names:
            continue

        rel_root = ET.fromstring(archive.read(rels_name).decode("utf-8", errors="replace"))
        for relationship in rel_root.findall("./rel:Relationship", _NS):
            image_name = _image_name_from_relationship(story_part.name, relationship, archive_names)
            if image_name is None:
                continue
            references.setdefault(
                image_name,
                EmbeddedImageReference(
                    image_name=image_name,
                    image_stem=sanitize_identifier(PurePosixPath(image_name).stem) or "embedded_image",
                    story_part_name=story_part.name,
                    story_part_kind=story_part.kind,
                ),
            )

    return list(references.values())


def sanitize_identifier(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()


def _image_name_from_relationship(story_part_name: str, relationship: ET.Element, archive_names: set[str]) -> str | None:
    if str(relationship.get("TargetMode", "")).strip().lower() == "external":
        return None
    rel_type = str(relationship.get("Type", "") or "")
    if not rel_type.endswith("/image"):
        return None
    target = str(relationship.get("Target", "") or "").strip()
    if not target:
        return None
    image_name = resolve_part_target(story_part_name, target)
    if image_name not in archive_names:
        return None
    if PurePosixPath(image_name).suffix.lower() not in IMAGE_SUFFIXES:
        return None
    return image_name
