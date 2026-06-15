from __future__ import annotations

import re
from xml.etree import ElementTree as ET

from .ooxml_constants import W_NS


def local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def normalize_text(value: str) -> str:
    lines: list[str] = []
    for line in value.replace("\xa0", " ").splitlines():
        collapsed = re.sub(r"\s+", " ", line).strip()
        if collapsed:
            lines.append(collapsed)
    return "\n".join(lines)


def extract_text(element: ET.Element) -> str:
    fragments: list[str] = []
    for node in element.iter():
        name = local_name(node.tag)
        if name in {"t", "delText"} and node.text:
            fragments.append(node.text)
        elif name in {"tab", "ptab"}:
            fragments.append("\t")
        elif name in {"br", "cr"}:
            fragments.append("\n")
    return "".join(fragments)


def optional_text(element: ET.Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    value = element.text.strip()
    return value or None


def word_on_off(element: ET.Element | None) -> bool:
    if element is None:
        return False
    value = element.get(f"{{{W_NS}}}val") or element.get("val")
    if value is None:
        return True
    return str(value).strip().lower() not in {"0", "false", "off"}


def word_half_points_to_pt(raw: str | None) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw) / 2.0
    except (TypeError, ValueError):
        return None
