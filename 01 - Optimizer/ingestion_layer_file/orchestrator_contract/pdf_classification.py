"""PDF classification policy for the Optimizer contract surface."""
from __future__ import annotations

from typing import Any

SCAN_CLASSIFICATION = "scan_pdf"
BORN_DIGITAL_CLASSIFICATION = "born_digital_pdf"


def classify_pdf_metadata(metadata: dict[str, Any], *, needs_ocr: bool) -> tuple[str, str]:
    is_scanned = bool(metadata.get("is_scanned", False))
    avg_chars = float(metadata.get("avg_chars_per_page", 0.0) or 0.0)
    text_blocks = int(metadata.get("text_block_count", 0) or 0)
    page_count = int(metadata.get("page_count", 0) or 0)
    if needs_ocr or is_scanned:
        reasons = ["needs_ocr=true" if needs_ocr else "", "is_scanned=true" if is_scanned else ""]
        detail = ", ".join(part for part in reasons if part)
        return SCAN_CLASSIFICATION, f"Scan-PDF erkannt ({detail or 'Scan-Heuristik aktiv'})."
    if page_count > 0 and text_blocks == 0 and avg_chars < 25.0:
        return SCAN_CLASSIFICATION, f"Scan-PDF erkannt (text_block_count=0, avg_chars_per_page={avg_chars:.1f})."
    text_density = str(metadata.get("text_density", "")).strip() or "unknown"
    has_images = bool(metadata.get("has_images", False))
    image_note = ", has_images=true" if has_images else ""
    return BORN_DIGITAL_CLASSIFICATION, (
        f"Born-digital PDF erkannt (text_density={text_density}, avg_chars_per_page={avg_chars:.1f}{image_note})."
    )

