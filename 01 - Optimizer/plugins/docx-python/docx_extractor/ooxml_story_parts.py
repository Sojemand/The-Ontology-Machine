from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from .ooxml_constants import DOC_REL_NS, NS, W_NS
from .ooxml_paths import resolve_part_target
from .ooxml_text import word_on_off

NON_STORY_PARTS = {
    "fontTable.xml",
    "numbering.xml",
    "settings.xml",
    "styles.xml",
    "stylesWithEffects.xml",
    "webSettings.xml",
}


@dataclass(frozen=True)
class StoryPart:
    name: str
    kind: str
    root: ET.Element
    xml_text: str


def load_story_parts(archive: ZipFile) -> list[StoryPart]:
    part_names = ordered_story_part_names(archive)
    if "word/document.xml" not in part_names:
        raise KeyError("word/document.xml")

    story_parts: list[StoryPart] = []
    for part_name in part_names:
        xml_text = archive.read(part_name).decode("utf-8", errors="replace")
        story_parts.append(
            StoryPart(
                name=part_name,
                kind=story_part_kind(part_name),
                root=ET.fromstring(xml_text),
                xml_text=xml_text,
            )
        )
    return story_parts


def ordered_story_part_names(archive: ZipFile) -> list[str]:
    archive_names = set(archive.namelist())
    ordered: list[str] = []
    seen: set[str] = set()
    active_header_parts, active_footer_parts = _active_header_footer_part_names(archive, archive_names)

    def add_names(names: list[str]) -> None:
        for name in names:
            if name in archive_names and name not in seen:
                ordered.append(name)
                seen.add(name)

    add_names(sorted(active_header_parts, key=story_sort_key) if active_header_parts else sorted(_matching_part_names(archive_names, "word/header"), key=story_sort_key))
    add_names(["word/document.xml"])
    add_names(sorted(active_footer_parts, key=story_sort_key) if active_footer_parts else sorted(_matching_part_names(archive_names, "word/footer"), key=story_sort_key))
    add_names([
        name
        for name in ("word/footnotes.xml", "word/endnotes.xml", "word/comments.xml", "word/glossary/document.xml")
        if name in archive_names
    ])
    constrained_story_parts = bool(active_header_parts or active_footer_parts)
    add_names(sorted(name for name in archive_names if is_story_part_name(name) and name not in seen))
    if constrained_story_parts:
        ordered = [
            name
            for name in ordered
            if not (
                (name.startswith("word/header") and name.endswith(".xml") and name not in active_header_parts)
                or (name.startswith("word/footer") and name.endswith(".xml") and name not in active_footer_parts)
            )
        ]
    return ordered


def story_sort_key(name: str) -> tuple[str, int, str]:
    stem = PurePosixPath(name).stem
    prefix = stem.rstrip("0123456789")
    suffix = stem[len(prefix):]
    return (prefix, int(suffix or 0), name)


def story_part_kind(name: str) -> str:
    path = PurePosixPath(name)
    if path.name.startswith("header"):
        return "header"
    if path.name.startswith("footer"):
        return "footer"
    if name == "word/document.xml":
        return "document"
    if path.name == "footnotes.xml":
        return "footnote"
    if path.name == "endnotes.xml":
        return "endnote"
    if path.name == "comments.xml":
        return "comment"
    if name == "word/glossary/document.xml":
        return "glossary"
    return "story"


def is_story_part_name(name: str) -> bool:
    path = PurePosixPath(name)
    if path.suffix.lower() != ".xml":
        return False
    if not name.startswith("word/"):
        return False
    if "/_rels/" in name or name.startswith("word/theme/"):
        return False
    if path.parent.as_posix() == "word" and path.name in NON_STORY_PARTS:
        return False
    return True


def _matching_part_names(archive_names: set[str], prefix: str) -> list[str]:
    return [name for name in archive_names if name.startswith(prefix) and name.endswith(".xml")]


def _active_header_footer_part_names(archive: ZipFile, archive_names: set[str]) -> tuple[set[str], set[str]]:
    if "word/document.xml" not in archive_names or "word/_rels/document.xml.rels" not in archive_names:
        return set(), set()

    document_root = ET.fromstring(archive.read("word/document.xml").decode("utf-8", errors="replace"))
    rel_root = ET.fromstring(archive.read("word/_rels/document.xml.rels").decode("utf-8", errors="replace"))
    rel_targets = {
        str(relationship.get("Id") or ""): resolve_part_target("word/document.xml", str(relationship.get("Target") or ""))
        for relationship in rel_root.findall("./rel:Relationship", NS)
    }
    even_and_odd = _uses_even_and_odd_headers(archive, archive_names)

    active_headers: set[str] = set()
    active_footers: set[str] = set()
    for section in document_root.findall(".//w:sectPr", NS):
        title_page = word_on_off(section.find("./w:titlePg", NS))
        header_refs = _section_part_references(section, rel_targets, prefix="header")
        footer_refs = _section_part_references(section, rel_targets, prefix="footer")
        active_headers.update(_select_active_part_names(header_refs, title_page=title_page, even_and_odd=even_and_odd))
        active_footers.update(_select_active_part_names(footer_refs, title_page=title_page, even_and_odd=even_and_odd))

    return active_headers, active_footers


def _uses_even_and_odd_headers(archive: ZipFile, archive_names: set[str]) -> bool:
    if "word/settings.xml" not in archive_names:
        return False
    root = ET.fromstring(archive.read("word/settings.xml").decode("utf-8", errors="replace"))
    return word_on_off(root.find("./w:evenAndOddHeaders", NS))


def _section_part_references(section: ET.Element, rel_targets: dict[str, str], *, prefix: str) -> dict[str, str]:
    references: dict[str, str] = {}
    for reference in section.findall(f"./w:{prefix}Reference", NS):
        ref_type = str(reference.get(f"{{{W_NS}}}type") or reference.get("type") or "").strip()
        rel_id = str(reference.get(f"{{{DOC_REL_NS}}}id") or reference.get("id") or "").strip()
        target = rel_targets.get(rel_id)
        if ref_type and target:
            references[ref_type] = target
    return references


def _select_active_part_names(references: dict[str, str], *, title_page: bool, even_and_odd: bool) -> set[str]:
    selected: set[str] = set()
    if title_page and references.get("first"):
        selected.add(references["first"])
    elif references.get("default"):
        selected.add(references["default"])
    if even_and_odd and references.get("even"):
        selected.add(references["even"])
    return selected


__all__ = ["StoryPart", "load_story_parts"]
