"""Runtime context tests for Corpus Builder Vision."""

from __future__ import annotations

from pathlib import Path

from corpus_builder.context import ModuleContext
from corpus_builder.context.types import ContextPaths


def test_module_context_exposes_named_path_contract(tmp_path: Path):
    context = ModuleContext(tmp_path)

    assert isinstance(context.paths, ContextPaths)
    assert context.runtime_dir == tmp_path / "runtime"
    assert context.bundled_runtime_dir == tmp_path / "runtime" / "python"
    assert context.state_dir == tmp_path / "state"


def test_module_context_from_package_root_targets_module_root() -> None:
    context = ModuleContext.from_package_root()

    assert context.module_root == Path(__file__).resolve().parents[2]
    assert context.config_path == context.module_root / "config" / "corpus_config.json"


def test_module_context_ensure_runtime_dirs_creates_mutable_directories(tmp_path: Path):
    context = ModuleContext(tmp_path)

    context.ensure_runtime_dirs()

    assert context.runtime_dir.is_dir()
    assert context.state_dir.is_dir()
    assert context.output_dir.is_dir()


def test_module_context_leaves_legacy_runtime_state_untouched(tmp_path: Path):
    context = ModuleContext(tmp_path)
    legacy_state_dir = context.runtime_dir / "state"
    legacy_state_dir.mkdir(parents=True)
    (legacy_state_dir / "keystore.enc").write_text("legacy-key", encoding="utf-8")
    context.state_dir.mkdir(parents=True)
    (context.state_dir / "semantic_release.active.json").write_text('{"current": true}', encoding="utf-8")

    context.ensure_runtime_dirs()

    assert not (context.state_dir / "keystore.enc").exists()
    assert (context.state_dir / "semantic_release.active.json").read_text(encoding="utf-8") == '{"current": true}'
    assert (legacy_state_dir / "keystore.enc").read_text(encoding="utf-8") == "legacy-key"


def test_module_context_resolve_path_uses_module_root_by_default(tmp_path: Path):
    context = ModuleContext(tmp_path)

    resolved = context.resolve_path("config/corpus_config.json")

    assert resolved == tmp_path / "config" / "corpus_config.json"


def test_module_context_resolve_path_honors_base_dir(tmp_path: Path):
    context = ModuleContext(tmp_path)
    base_dir = tmp_path / "artifacts"

    resolved = context.resolve_path("normalized/doc.json", base_dir=base_dir)

    assert resolved == base_dir / "normalized" / "doc.json"


def test_module_context_resolve_optional_path_handles_empty_values(tmp_path: Path):
    context = ModuleContext(tmp_path)

    assert context.resolve_optional_path(None) is None
    assert context.resolve_optional_path("  ") is None
    assert context.resolve_optional_path(Path("state/semantic_release.active.json")) == tmp_path / "state" / "semantic_release.active.json"
