from __future__ import annotations

from types import SimpleNamespace
import sys

from ingestion_layer_vision.extractors import pdf_text


class _FakePage:
    def __init__(
        self,
        *,
        text: str = "",
        tables: list | None = None,
        images: list | None = None,
        annots=None,
        text_error: str | None = None,
    ) -> None:
        self._text = text
        self._tables = tables or []
        self._images = images or []
        self.annots = annots
        self._text_error = text_error

    def extract_text(self) -> str:
        if self._text_error:
            raise RuntimeError(self._text_error)
        return self._text

    def extract_tables(self) -> list:
        return self._tables

    @property
    def images(self) -> list:
        return self._images


class _FakePdf:
    def __init__(self, pages: list[_FakePage], metadata: dict | None = None) -> None:
        self.pages = pages
        self.metadata = metadata or {}

    def __enter__(self) -> _FakePdf:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        del exc_type, exc, tb
        return False


class _FakePdfPlumber:
    def __init__(self, pdf: _FakePdf | None = None, error: Exception | None = None) -> None:
        self._pdf = pdf
        self._error = error

    def open(self, _path: str) -> _FakePdf:
        if self._error is not None:
            raise self._error
        assert self._pdf is not None
        return self._pdf


class TestPdfTextExtractor:
    def test_surface_import_and_selftest(self, monkeypatch) -> None:
        monkeypatch.setitem(sys.modules, "pdfplumber", SimpleNamespace(open=lambda _path: None))

        assert callable(pdf_text.extract)
        assert pdf_text.selftest() == {"status": "ok", "version": "2.0.0"}

    def test_extract_pdf_blocks_and_metadata(self, monkeypatch, tmp_path) -> None:
        source = tmp_path / "sample.pdf"
        source.write_bytes(b"%PDF-1.7 fake")
        fake_pdf = _FakePdf(
            [
                _FakePage(text=("A" * 60) + "\n\n" + ("B" * 20)),
                _FakePage(
                    text="",
                    tables=[[["", "42"], ["Name", "Ada"]]],
                    images=[{"x0": 0}],
                    annots=[object()],
                ),
            ],
            metadata={"pdf:PDFVersion": "1.7"},
        )
        monkeypatch.setitem(sys.modules, "pdfplumber", _FakePdfPlumber(pdf=fake_pdf))

        result = pdf_text.extract(source)

        assert result["status"] == "success"
        assert result["errors"] == []
        assert result["needs_ocr"] is False
        assert result["metadata"] == {
            "page_count": 2,
            "is_scanned": False,
            "has_images": True,
            "text_density": "sparse",
            "avg_chars_per_page": 41.0,
            "text_block_count": 2,
            "table_cell_count": 4,
            "pdf_version": "1.7",
            "has_annotations": True,
        }
        assert [block["id"] for block in result["blocks"]] == [
            "page1_para_0",
            "page1_para_1",
            "page2_table0_R0_C0",
            "page2_table0_R0_C1",
            "page2_table0_R1_C0",
            "page2_table0_R1_C1",
        ]
        assert result["blocks"][0]["position"] == {
            "sheet": None,
            "row": None,
            "col": None,
            "col_letter": None,
            "page": 1,
            "paragraph_index": 0,
            "table_index": None,
        }
        assert result["blocks"][-1]["value"] == "Ada"

    def test_page_stage_failure_returns_error_envelope(self, monkeypatch, tmp_path) -> None:
        source = tmp_path / "broken.pdf"
        source.write_bytes(b"%PDF-1.7 fake")
        fake_pdf = _FakePdf([_FakePage(text_error="decode failed")])
        monkeypatch.setitem(sys.modules, "pdfplumber", _FakePdfPlumber(pdf=fake_pdf))

        result = pdf_text.extract(source)

        assert result["status"] == "error"
        assert result["blocks"] == []
        assert result["metadata"] == {}
        assert result["needs_ocr"] is False
        assert result["errors"] == ["adapter.page_text[1]: decode failed"]
