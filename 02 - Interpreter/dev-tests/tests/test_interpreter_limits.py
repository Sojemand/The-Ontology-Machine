from __future__ import annotations

import copy
from pathlib import Path

import pytest

from llm_interpreter.interpreter import _validate_request, process_batch
from llm_interpreter.models import InterpreterConfig
from llm_interpreter.providers import ProviderError


def test_validate_request_rejects_too_many_page_assets(sample_request, tmp_path) -> None:
    request = copy.deepcopy(sample_request)
    request["page_assets"].append(_build_page(tmp_path, 3))
    request["source"]["page_count"] = 3

    with pytest.raises(ProviderError, match="Limit von 2 Seiten"):
        _validate_request(request, InterpreterConfig(max_page_assets=2))


def test_validate_request_rejects_total_asset_limit(sample_request) -> None:
    total_bytes = sum(Path(page["path"]).stat().st_size for page in sample_request["page_assets"])

    with pytest.raises(ProviderError, match="Gesamtlimit"):
        _validate_request(sample_request, InterpreterConfig(max_request_asset_bytes=total_bytes - 1))


def test_process_batch_rejects_zero_workers(tmp_path) -> None:
    with pytest.raises(ProviderError, match="num_workers muss positiv sein"):
        process_batch(tmp_path, tmp_path / "out", InterpreterConfig(max_workers=4), num_workers=0)


def test_process_batch_rejects_worker_count_above_limit(tmp_path) -> None:
    with pytest.raises(ProviderError, match="Limit von 4"):
        process_batch(tmp_path, tmp_path / "out", InterpreterConfig(max_workers=4), num_workers=5)


def _build_page(tmp_path, page: int) -> dict[str, object]:
    path = tmp_path / "pages" / f"page_{page:03d}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + bytes(f"page-{page}", encoding="ascii"))
    return {"page": page, "path": str(path), "media_type": "image/png"}
