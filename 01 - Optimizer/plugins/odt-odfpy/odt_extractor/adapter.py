"""Runtime and ODF adapters for the odt-odfpy extractor."""
from __future__ import annotations

from pathlib import Path

from .types import OdtDocumentSnapshot, OdtStageError, OdtTableCellSnapshot, OdtTextSnapshot


def ensure_odfpy() -> None:
    _import_runtime()


def load_document_snapshot(source: Path) -> OdtDocumentSnapshot:
    load, odf_meta, odf_table = _import_runtime()
    try:
        document = load(str(source))
    except Exception as exc:
        raise OdtStageError("adapter.load", str(exc)) from exc

    try:
        body = document.body
        text_nodes = tuple(_collect_text_snapshots(body))
        table_cells, table_col_counts = _collect_table_cells(body, odf_table)
        return OdtDocumentSnapshot(
            text_nodes=text_nodes,
            table_cells=table_cells,
            table_count=len(table_col_counts),
            table_col_counts=table_col_counts,
            author=_read_author(getattr(document, "meta", None), odf_meta),
        )
    except OdtStageError:
        raise
    except Exception as exc:
        raise OdtStageError("adapter.read", str(exc)) from exc


def _import_runtime():
    try:
        from odf.opendocument import load
        from odf import meta as odf_meta
        from odf import table as odf_table
    except ImportError as exc:
        raise OdtStageError("adapter.runtime", str(exc)) from exc
    return load, odf_meta, odf_table


def _collect_text_snapshots(body) -> list[OdtTextSnapshot]:
    elements: list[object] = []
    for child in getattr(body, "childNodes", ()):
        _collect_narrative_elements(child, elements)
    snapshots: list[OdtTextSnapshot] = []
    for element in elements:
        text = _flatten_text(element).strip()
        if text:
            snapshots.append(
                OdtTextSnapshot(
                    kind=_tag_name(element),
                    text=text,
                    outline_level=_read_attribute(element, "outlinelevel"),
                )
            )
    return snapshots


def _collect_narrative_elements(node, result: list[object]) -> None:
    tag = _tag_name(node)
    if tag == "table":
        return
    if tag in {"p", "h"}:
        result.append(node)
        return
    for child in getattr(node, "childNodes", ()):
        _collect_narrative_elements(child, result)


def _collect_table_cells(body, odf_table) -> tuple[tuple[OdtTableCellSnapshot, ...], tuple[int, ...]]:
    cells: list[OdtTableCellSnapshot] = []
    col_counts: list[int] = []
    for table_index, table in enumerate(body.getElementsByType(odf_table.Table)):
        max_cols = 0
        for row_index, row in enumerate(table.getElementsByType(odf_table.TableRow)):
            row_cells = row.getElementsByType(odf_table.TableCell)
            max_cols = max(max_cols, len(row_cells))
            for col_index, cell in enumerate(row_cells):
                text = _flatten_text(cell).strip()
                if text:
                    cells.append(
                        OdtTableCellSnapshot(
                            table_index=table_index,
                            row_index=row_index,
                            col_index=col_index,
                            text=text,
                        )
                    )
        col_counts.append(max_cols)
    return tuple(cells), tuple(col_counts)


def _read_author(meta_elem, odf_meta) -> str | None:
    if meta_elem is None:
        return None
    for attr_name in ("InitialCreator", "Creator"):
        creator_type = getattr(odf_meta, attr_name, None)
        if creator_type is None:
            continue
        try:
            matches = meta_elem.getElementsByType(creator_type)
        except Exception:
            return None
        if matches:
            author = _flatten_text(matches[0]).strip()
            if author:
                return author
    return None


def _flatten_text(element) -> str:
    parts: list[str] = []
    for child in getattr(element, "childNodes", ()):
        if hasattr(child, "data"):
            parts.append(str(child.data))
        else:
            parts.append(_flatten_text(child))
    return "".join(parts)


def _tag_name(node) -> str:
    qname = getattr(node, "qname", None)
    if isinstance(qname, tuple) and len(qname) > 1:
        return str(qname[1])
    return ""


def _read_attribute(node, name: str) -> str | None:
    getter = getattr(node, "getAttribute", None)
    if callable(getter):
        try:
            value = getter(name)
        except Exception:
            return None
        return None if value in (None, "") else str(value)
    return None
