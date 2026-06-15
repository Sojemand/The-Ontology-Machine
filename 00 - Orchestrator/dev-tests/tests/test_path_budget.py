from __future__ import annotations

from pathlib import Path

from orchestrator.pipeline import path_budget


def test_runtime_doc_dir_uses_short_hash_stage() -> None:
    runtime_root = Path("C:/artifacts/logs/orchestrator/runs/2026-03-29T09-58-15.292427+00-00")

    target = path_budget.runtime_doc_dir(runtime_root, "sha256:4452a9c2abcdef")

    assert target == runtime_root / "d.4452a9c2"


def test_bundle_member_name_keeps_short_names_unchanged(tmp_path: Path) -> None:
    bundle_path = tmp_path / "errors" / "Documents" / "Interpreter" / "doc.bundle"

    name = path_budget.bundle_member_name(bundle_path, "source", Path("doc.pdf"))

    assert name == "source__doc.pdf"


def test_bundle_member_name_truncates_only_when_budget_is_exceeded() -> None:
    bundle_path = Path(
        "C:/Users/Norma/Desktop/File Optimzer/Artefacts/errors/Documents/Interpreter/"
        "201611136_V_-_L_-_Reinhard_Feinmechanik_Dietzenbach_-_Anlieferung_von_20_St_ck_R.4452a9c2"
    )
    source = Path(
        "201611136 V - L - Reinhard Feinmechanik Dietzenbach - "
        "Anlieferung von 20 Stuck Rohlingen O60 x 440-290mm lang .docx.raw.json"
    )

    name = path_budget.bundle_member_name(bundle_path, "raw", source, index=1)

    assert name.startswith("raw__01__")
    assert name.endswith(".raw.json")
    assert len(str(bundle_path / name)) <= path_budget.WINDOWS_PATH_BUDGET


def test_budgeted_page_name_preserves_page_tail_when_truncated() -> None:
    parent = Path(
        "C:/Users/Norma/Desktop/File Optimzer/Artefacts/Error Cases/Validator/Documents/requests/"
        "BK-20220671 Hin - SKW Piesteritz - GR 2022 - diverse Maschinen - Schmidt Transporte.docx"
    )
    slug = (
        "BK-20220671_Hin_-_SKW_Piesteritz_-_GR_2022_-_diverse_Maschinen_-_Schmidt_"
        "Transporte.0b0a5210.p001.of002"
    )

    name = path_budget.budgeted_page_name(parent, slug, suffix=".structured.json")

    assert name.endswith(".p001.of002.structured.json")
    assert len(str(parent / name)) <= path_budget.WINDOWS_PATH_BUDGET


def test_budgeted_stage_name_preserves_page_tail_before_known_suffix() -> None:
    parent = Path(
        "C:/Users/Norma/Desktop/File Optimzer/Artefacts/Error Cases/Validator/Documents/raw_extracts/"
        "BK-20220671 Hin - SKW Piesteritz - GR 2022 - diverse Maschinen"
    )
    name = (
        "BK-20220671_Hin_-_SKW_Piesteritz_-_GR_2022_-_diverse_Maschinen_-_Schmidt_"
        "Transporte.0b0a5210.p001.of002.raw.json"
    )

    budgeted = path_budget.budgeted_stage_name(parent, name)

    assert budgeted.endswith(".p001.of002.raw.json")
    assert len(str(parent / budgeted)) <= path_budget.WINDOWS_PATH_BUDGET


def test_budgeted_relative_path_respects_parent_budget() -> None:
    root = Path(
        "C:/Users/Norma/Desktop/File Optimzer/Artefacts/Error Cases/Validator/Documents/requests"
    )
    relative = Path(
        "BK-20220671 Hin - SKW Piesteritz - GR 2022 - diverse Maschinen - Schmidt Transporte.docx"
    )

    target = path_budget.budgeted_relative_path(root, relative)

    assert len(str(root / target)) <= path_budget.WINDOWS_PATH_BUDGET

