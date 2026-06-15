from __future__ import annotations

from pathlib import Path

import pytest

from tests.pipeline_harness import create_source, load_single_record, make_engine, make_ui_state, route_root


def test_raster_image_stays_on_images_route(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state, "scan.jpg", content="image")

    summary = make_engine(tmp_path, scenarios={}).run(ui_state)

    record = load_single_record(tmp_path)
    assert summary.success == 1
    assert record.route_family == "Documents"
    assert record.optimizer_module_key == "optimizer"
    assert record.interpreter_module_key == "interpreter"
    assert list((route_root(ui_state, "Documents") / "raw_extracts").glob("*.raw.json"))


def test_msg_input_routes_to_optimizer(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state, "mail.msg", content="mail")

    summary = make_engine(tmp_path, scenarios={}).run(ui_state)

    record = load_single_record(tmp_path)
    assert summary.success == 1
    assert record.route_family == "Documents"
    assert record.optimizer_module_key == "optimizer"
    assert record.interpreter_module_key == "interpreter"
    assert record.intake_reason == "File format .msg detected."
    assert list((route_root(ui_state, "Documents") / "raw_extracts").glob("*.raw.json"))


@pytest.mark.parametrize("filename", ["mail.eml", "mail.emlx", "mail.mbox", "mail.oft", "mail.pst", "mail.ost"])
def test_other_mail_inputs_route_to_optimizer(tmp_path: Path, filename: str) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state, filename, content="mail")

    summary = make_engine(tmp_path, scenarios={}).run(ui_state)

    record = load_single_record(tmp_path)
    assert summary.success == 1
    assert record.route_family == "Documents"
    assert record.optimizer_module_key == "optimizer"
    assert record.interpreter_module_key == "interpreter"
    assert record.intake_reason == f"File format {Path(filename).suffix.lower()} detected."
