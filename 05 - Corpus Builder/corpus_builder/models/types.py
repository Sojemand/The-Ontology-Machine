"""Named config and request types for the Corpus Builder surface."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DatabaseConfig:
    corpus_db: str = "./output/corpus.db"


@dataclass
class EmbeddingConfig:
    dimensions: int = 1536
    batch_size: int = 50
    max_text_chars: int = 12000


@dataclass
class ArchiveConfig:
    enabled: bool = True
    keep_archived: bool = True


@dataclass
class FTSConfig:
    enabled: bool = True
    tokenizer: str = "unicode61"


@dataclass
class SourceConfig:
    page_images_dir: str = ""
    persist_page_images_in_db: bool = True
    persist_original_artifact_in_db: bool = False
    max_original_artifact_bytes: int = 52428800
    max_page_image_bytes: int = 10485760
    max_page_image_total_bytes: int = 104857600


@dataclass
class SemanticConfig:
    published_release_path: str = "./config/semantic_release.default.json"
    active_release_path: str = "./state/semantic_release.active.json"
    release_report_path: str = "./state/semantic_release_report.json"


@dataclass
class CorpusConfig:
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    embeddings: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    archive: ArchiveConfig = field(default_factory=ArchiveConfig)
    fts: FTSConfig = field(default_factory=FTSConfig)
    source: SourceConfig = field(default_factory=SourceConfig)
    semantic: SemanticConfig = field(default_factory=SemanticConfig)


@dataclass
class LoadBundle:
    normalized_path: Path
    structured_path: Path | None
    validation_path: Path | None
    raw_path: Path | None
    corpus_db_path: str


@dataclass
class EmbeddingRuntimeSettings:
    model: str


@dataclass
class EmbeddingRequest:
    corpus_db_path: str
    runtime_settings: EmbeddingRuntimeSettings
