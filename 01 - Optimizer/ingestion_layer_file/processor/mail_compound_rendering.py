"""Rendering helpers for mail body and attachment pages."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .mail_compound_types import MAX_MAIL_PAGE_BYTES, MAX_MAIL_PAGE_HEIGHT_PX


@dataclass(frozen=True)
class _TextRenderContext:
    width_px: int
    margin_px: int
    line_stride_px: int
    wrapped_lines: list[tuple[str, object]]


def render_text_page(*, lines: list[str], output_path: Path, processor) -> Path:
    context = _prepare_text_render_context(lines=lines, processor=processor)
    body_height = _text_page_height(context.wrapped_lines, context)
    if body_height > MAX_MAIL_PAGE_HEIGHT_PX:
        raise RuntimeError(f"Mail-Nachricht ist fuer ein einzelnes PNG zu lang ({body_height}px).")
    _write_text_page(output_path, context=context, wrapped_lines=context.wrapped_lines)
    _ensure_safe_file_size(output_path, label="Mail-Nachricht")
    return output_path


def render_text_pages(*, lines: list[str], output_path: Path, processor) -> list[Path]:
    """Render a long mail body into bounded PNG slices without splitting source text blocks."""
    context = _prepare_text_render_context(lines=lines, processor=processor)
    max_lines_per_page = _max_wrapped_lines_per_page(context)
    chunks = _chunk_wrapped_lines(context.wrapped_lines, max_lines_per_page)
    page_paths: list[Path] = []
    for page_index, chunk in enumerate(chunks, start=1):
        page_path = _text_page_part_path(output_path, page_index)
        _write_text_page(page_path, context=context, wrapped_lines=chunk)
        _ensure_safe_file_size(page_path, label="Mail-Seite")
        page_paths.append(page_path)
    return page_paths


def render_image_attachment(source_path: Path, output_path: Path, processor) -> Path:
    from PIL import Image

    output_path.parent.mkdir(parents=True, exist_ok=True)
    width_px = processor._config.render_width_px
    height_px = processor._config.render_height_px
    with Image.open(source_path) as image:
        image = image.convert("L")
        image.thumbnail((width_px, height_px))
        canvas = Image.new("L", (width_px, height_px), color=255)
        canvas.paste(image, (max(0, (width_px - image.width) // 2), max(0, (height_px - image.height) // 2)))
        canvas.save(output_path, "PNG", optimize=True)
    return output_path


def _prepare_text_render_context(*, lines: list[str], processor) -> _TextRenderContext:
    from PIL import Image, ImageDraw

    width_px = processor._config.render_width_px
    margin_px = max(40, int(width_px * 0.04))
    text_width = max(200, width_px - margin_px * 2)
    body_font = _load_font(int(processor._config.default_font_size_pt * 3.2))
    header_font = _load_font(int(processor._config.heading_font_size_pt * 2.2))
    probe = ImageDraw.Draw(Image.new("L", (width_px, 64), color=255))
    wrapped: list[tuple[str, object]] = []
    line_height = max(_font_line_height(body_font), _font_line_height(header_font))
    for index, raw_line in enumerate(lines):
        is_header = index < 6 and ":" in raw_line and raw_line.split(":", 1)[0] in {"From", "To", "Cc", "Subject", "Date", "Attachments"}
        font = header_font if is_header else body_font
        wrapped.extend((segment, font) for segment in _wrap_line(probe, raw_line, font, text_width))
        if raw_line == "":
            wrapped.append(("", body_font))
    return _TextRenderContext(
        width_px=width_px,
        margin_px=margin_px,
        line_stride_px=line_height + 8,
        wrapped_lines=wrapped,
    )


def _write_text_page(output_path: Path, *, context: _TextRenderContext, wrapped_lines: list[tuple[str, object]]) -> None:
    from PIL import Image, ImageDraw

    output_path.parent.mkdir(parents=True, exist_ok=True)
    body_height = _text_page_height(wrapped_lines, context)
    image = Image.new("L", (context.width_px, body_height), color=255)
    draw = ImageDraw.Draw(image)
    cursor_y = context.margin_px
    for text, font in wrapped_lines:
        if text:
            draw.multiline_text((context.margin_px, cursor_y), text, fill=0, font=font, spacing=6)
            cursor_y += text.count("\n") * (_font_line_height(font) + 6)
        cursor_y += _font_line_height(font) + 8
    image.save(output_path, "PNG", optimize=True)


def _text_page_height(wrapped_lines: list[tuple[str, object]], context: _TextRenderContext) -> int:
    return context.margin_px * 2 + max(1, len(wrapped_lines)) * context.line_stride_px


def _max_wrapped_lines_per_page(context: _TextRenderContext) -> int:
    usable_height = max(context.line_stride_px, MAX_MAIL_PAGE_HEIGHT_PX - context.margin_px * 2)
    return max(1, usable_height // context.line_stride_px)


def _chunk_wrapped_lines(wrapped_lines: list[tuple[str, object]], max_lines_per_page: int) -> list[list[tuple[str, object]]]:
    if not wrapped_lines:
        return [[]]
    return [
        wrapped_lines[index : index + max_lines_per_page]
        for index in range(0, len(wrapped_lines), max_lines_per_page)
    ]


def _text_page_part_path(output_path: Path, page_index: int) -> Path:
    if page_index == 1:
        return output_path
    return output_path.with_name(f"{output_path.stem}_part{page_index:04d}{output_path.suffix}")


def _ensure_safe_file_size(output_path: Path, *, label: str) -> None:
    if output_path.stat().st_size > MAX_MAIL_PAGE_BYTES:
        raise RuntimeError(f"{label} ueberschreitet das sichere Bildbudget: {output_path.name}")


def _wrap_line(draw, text: str, font, max_width: int) -> list[str]:
    payload = str(text or "")
    if not payload:
        return [""]
    words = payload.split()
    if not words:
        return [payload]
    lines = [words[0]]
    for word in words[1:]:
        candidate = f"{lines[-1]} {word}"
        if draw.textlength(candidate, font=font) <= max_width:
            lines[-1] = candidate
            continue
        lines.extend(_hard_wrap_overflow(draw, lines.pop(), font, max_width))
        lines.append(word)
    return [segment for line in lines for segment in _hard_wrap_overflow(draw, line, font, max_width)]


def _hard_wrap_overflow(draw, text: str, font, max_width: int) -> list[str]:
    payload = str(text or "")
    if draw.textlength(payload, font=font) <= max_width:
        return [payload]
    pieces: list[str] = []
    current = ""
    for character in payload:
        candidate = f"{current}{character}"
        if current and draw.textlength(candidate, font=font) > max_width:
            pieces.append(current)
            current = character
            continue
        current = candidate
    if current:
        pieces.append(current)
    return pieces


def _font_line_height(font) -> int:
    try:
        ascent, descent = font.getmetrics()
        return ascent + descent
    except Exception:
        return 32


def _load_font(size: int):
    from PIL import ImageFont

    for candidate in ("DejaVuSans.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(candidate, max(12, size))
        except OSError:
            continue
    return ImageFont.load_default()
