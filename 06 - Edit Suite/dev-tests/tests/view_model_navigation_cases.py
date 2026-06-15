from __future__ import annotations

from edit_suite.registry.types import RegistrySnapshot
from edit_suite.surfaces.types import SectionModel, SurfaceModel
from edit_suite.ui import view_model
from view_model_support import entry


def test_view_model_keeps_module_first_order_and_fixed_sections() -> None:
    snapshot = RegistrySnapshot(
        generated_at="now",
        source="live",
        stale=False,
        message="",
        entries=(entry("00 - Orchestrator", "missing_edit_contract"), entry("04 - Normalizer", "ready")),
    )
    items = view_model.list_items(snapshot)
    assert [item.key for item in items] == ["00 - Orchestrator", "04 - Normalizer"]
    assert [item.title for item in items] == ["Orchestrator", "Normalizer"]
    assert items[0].subtitle == "Notice: no contract yet"
    assert items[1].subtitle == ""
    detail = view_model.detail_view(snapshot.entries[0])
    assert [section.name for section in detail.sections] == [
        "Summary",
        "Settings",
        "Prompts/Assets",
        "Operations",
        "Preview/Drift",
    ]
    assert "owner-provided" in detail.sections[1].body


def test_list_items_use_compact_sidebar_titles_for_optimizer_and_interpreter_slots() -> None:
    snapshot = RegistrySnapshot(
        generated_at="now",
        source="live",
        stale=False,
        message="",
        entries=(
            entry("01 - Optimizer", "ready"),
            entry("02 - Interpreter", "ready"),
            entry("03 - Validator", "ready"),
            entry("05 - Corpus Builder", "ready"),
        ),
    )

    items = view_model.list_items(snapshot)

    assert [item.title for item in items] == ["Optimizer", "Interpreter", "Validator", "Corpus Builder"]
    assert all(item.subtitle == "" for item in items)


def test_preferred_module_key_picks_first_ready_when_saved_selection_is_not_ready() -> None:
    snapshot = RegistrySnapshot(
        generated_at="now",
        source="live",
        stale=False,
        message="",
        entries=(
            entry("00 - Orchestrator", "missing_edit_contract"),
            entry("01 - Optimizer", "ready"),
            entry("04 - Normalizer", "ready"),
        ),
    )

    assert view_model.preferred_module_key(snapshot, "00 - Orchestrator") == "01 - Optimizer"


def test_preferred_section_promotes_first_populated_edit_tab_over_summary() -> None:
    populated = SurfaceModel(
        surface_id="optimizer.settings",
        label="Settings",
        kind="settings",
        editable=True,
        editor_kind="form",
        descriptor={},
        value={"parallel_workers": 1},
        draft={"parallel_workers": 1},
        operation_links=(),
    )
    sections = (
        SectionModel("Summary", "Summary", "summary", "body"),
        SectionModel("Settings", "Settings", "settings", "body", surfaces=(populated,)),
        SectionModel("Prompts/Assets", "Prompts/Assets", "prompts", "body"),
    )

    assert view_model.preferred_section(sections, "Summary") == "Settings"
    assert view_model.preferred_section(sections, "Prompts/Assets") == "Prompts/Assets"
