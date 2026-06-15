"""Typed path carriers and constants for source-package authoring files."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SOURCE_ROOT_RELATIVE_PATH = Path("config") / "taxonomy_sources"


@dataclass(frozen=True, slots=True)
class ProjectionTextSourcePath:
    locale: str
    text_path: Path

    def relative_file(self, root: Path) -> str:
        return self.text_path.relative_to(root).as_posix()


@dataclass(frozen=True, slots=True)
class ProjectionSourcePaths:
    projection_id: str
    core_path: Path
    texts: tuple[ProjectionTextSourcePath, ...]

    @property
    def text_path(self) -> Path:
        if not self.texts:
            raise KeyError(f"Keine Textdatei vorhanden: {self.projection_id}")
        return self.texts[0].text_path

    def text_path_for(self, locale: str) -> Path:
        for item in self.texts:
            if item.locale == locale:
                return item.text_path
        raise KeyError(f"Locale nicht gefunden: {self.projection_id}.{locale}")

    def relative_files(self, root: Path) -> tuple[str, ...]:
        files = [self.core_path.relative_to(root).as_posix()]
        files.extend(item.relative_file(root) for item in self.texts)
        return tuple(files)


@dataclass(frozen=True, slots=True)
class LocaleSourcePaths:
    locale: str
    master_text_path: Path
    glossary_path: Path
    glossary_exists: bool = False

    def relative_files(self, root: Path) -> tuple[str, ...]:
        files = [self.master_text_path.relative_to(root).as_posix()]
        if self.glossary_exists:
            files.append(self.glossary_path.relative_to(root).as_posix())
        return tuple(files)


@dataclass(frozen=True, slots=True)
class SourcePackagePaths:
    root: Path
    release_path: Path
    master_core_path: Path
    locales: tuple[LocaleSourcePaths, ...]
    projections: tuple[ProjectionSourcePaths, ...]

    @property
    def master_text_path(self) -> Path:
        if not self.locales:
            raise KeyError("Keine Locale-Dateien vorhanden.")
        return self.locales[0].master_text_path

    def locale_paths(self, locale: str) -> LocaleSourcePaths:
        for item in self.locales:
            if item.locale == locale:
                return item
        raise KeyError(f"Locale nicht gefunden: {locale}")

    def all_paths(self) -> tuple[Path, ...]:
        paths = [
            self.release_path,
            self.master_core_path,
        ]
        for locale_paths in self.locales:
            paths.append(locale_paths.master_text_path)
        for locale_paths in self.locales:
            if locale_paths.glossary_exists:
                paths.append(locale_paths.glossary_path)
        for projection in self.projections:
            paths.append(projection.core_path)
            paths.extend(item.text_path for item in projection.texts)
        return tuple(paths)

    def relative_files(self) -> tuple[str, ...]:
        files = [
            self.release_path.relative_to(self.root).as_posix(),
            self.master_core_path.relative_to(self.root).as_posix(),
        ]
        for locale_paths in self.locales:
            files.append(locale_paths.master_text_path.relative_to(self.root).as_posix())
        for locale_paths in self.locales:
            if locale_paths.glossary_exists:
                files.append(locale_paths.glossary_path.relative_to(self.root).as_posix())
        for projection in self.projections:
            files.extend(projection.relative_files(self.root))
        return tuple(files)
