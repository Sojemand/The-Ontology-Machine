from __future__ import annotations

from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from optimizer_ocr import extract_page_assets

from .embedded_image_ocr import embedded_image_part_names, extract_embedded_image_ocr_blocks
from .ooxml_constants import NS, W_NS
from .ooxml_story_parts import load_story_parts
from .ooxml_text import extract_text, local_name, normalize_text, optional_text, word_half_points_to_pt, word_on_off
from .types import WordDocumentSnapshot, WordParagraphSnapshot, WordTableCellSnapshot


def load_ooxml_snapshot(source: Any, config: dict[str, Any]) -> WordDocumentSnapshot:
    with ZipFile(source) as archive:
        story_parts = load_story_parts(archive)
        paragraphs: list[WordParagraphSnapshot] = []
        table_cells: list[WordTableCellSnapshot] = []
        table_col_counts: list[int] = []

        paragraph_index = 0
        table_index = 0
        has_track_changes = False

        for story_part in story_parts:
            has_track_changes = has_track_changes or "<w:ins " in story_part.xml_text or "<w:del " in story_part.xml_text

            story_paragraphs = paragraph_snapshots_from_root(story_part.root, paragraph_index)
            paragraphs.extend(story_paragraphs)
            paragraph_index += len(story_paragraphs)

            story_table_cells, story_table_col_counts = table_snapshots_from_root(story_part.root, table_index)
            table_cells.extend(story_table_cells)
            table_col_counts.extend(story_table_col_counts)
            table_index += len(story_table_col_counts)

        author, last_modified_by = load_core_properties(archive)
        image_names = embedded_image_part_names(archive)
        ocr_blocks, ocr_metadata = extract_embedded_image_ocr_blocks(
            archive,
            story_parts,
            paragraph_index,
            config,
            extract_page_assets=extract_page_assets,
        )

        return WordDocumentSnapshot(
            paragraphs=tuple(paragraphs),
            table_cells=tuple(table_cells),
            table_count=len(table_col_counts),
            table_col_counts=tuple(table_col_counts),
            has_images=bool(image_names),
            image_count=len(image_names),
            author=author,
            last_modified_by=last_modified_by,
            has_track_changes=has_track_changes,
            ocr_blocks=ocr_blocks,
            ocr_metadata=ocr_metadata,
        )


def paragraph_snapshots_from_root(root: ET.Element, start_index: int) -> list[WordParagraphSnapshot]:
    snapshots: list[WordParagraphSnapshot] = []
    paragraph_index = start_index

    def visit(element: ET.Element, *, inside_table: bool) -> None:
        nonlocal paragraph_index
        if local_name(element.tag) == "p" and not inside_table:
            snapshot = paragraph_snapshot_from_element(element, paragraph_index)
            if snapshot is not None:
                snapshots.append(snapshot)
                paragraph_index += 1
            return
        next_inside_table = inside_table or local_name(element.tag) == "tbl"
        for child in list(element):
            visit(child, inside_table=next_inside_table)

    visit(root, inside_table=False)
    return snapshots


def paragraph_snapshot_from_element(paragraph: ET.Element, index: int) -> WordParagraphSnapshot | None:
    text = normalize_text(extract_text(paragraph))
    if not text:
        return None
    style_name = ""
    style = paragraph.find("./w:pPr/w:pStyle", NS)
    if style is not None:
        style_name = (style.get(f"{{{W_NS}}}val") or style.get("val") or "").strip()

    bold = False
    font_size: float | None = None
    for run in paragraph.findall(".//w:r", NS):
        properties = run.find("./w:rPr", NS)
        if properties is None:
            continue
        bold = bold or word_on_off(properties.find("./w:b", NS))
        if font_size is None:
            size = properties.find("./w:sz", NS)
            if size is not None:
                font_size = word_half_points_to_pt(size.get(f"{{{W_NS}}}val") or size.get("val"))

    return WordParagraphSnapshot(index=index, text=text, style_name=style_name, bold=bold, font_size=font_size)


def table_snapshots_from_root(root: ET.Element, start_table_index: int) -> tuple[list[WordTableCellSnapshot], list[int]]:
    cells: list[WordTableCellSnapshot] = []
    col_counts: list[int] = []
    table_index = start_table_index

    for table in root.findall(".//w:tbl", NS):
        rows = table.findall("./w:tr", NS)
        max_cols = 0
        for row_index, row in enumerate(rows):
            row_cells = row.findall("./w:tc", NS)
            max_cols = max(max_cols, len(row_cells))
            for col_index, cell in enumerate(row_cells):
                text = normalize_text(extract_text(cell))
                if text:
                    cells.append(WordTableCellSnapshot(table_index=table_index, row_index=row_index, col_index=col_index, text=text))
        col_counts.append(max_cols)
        table_index += 1

    return cells, col_counts


def load_core_properties(archive: ZipFile) -> tuple[str | None, str | None]:
    if "docProps/core.xml" not in archive.namelist():
        return None, None

    root = ET.fromstring(archive.read("docProps/core.xml").decode("utf-8", errors="replace"))
    author = optional_text(root.find("./dc:creator", NS))
    last_modified_by = optional_text(root.find("./cp:lastModifiedBy", NS))
    return author, last_modified_by


__all__ = ["load_ooxml_snapshot"]
