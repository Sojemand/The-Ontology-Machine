"""Action metadata for Edit Suite operation cards."""
from __future__ import annotations

from .config_repository import read_settings

_CONTRACT_MODULE = "corpus_builder.orchestrator_contract"
_MODEL_DEFAULT = "text-embedding-3-large"


def action_buttons(surface_id: str, *, module_root, settings: dict | None = None) -> list[dict]:
    settings = settings if settings is not None else read_settings(module_root)
    corpus_db = str(settings.get("database.corpus_db") or "./output/corpus.db")
    if surface_id == "corpus_builder.settings":
        return _settings_actions(corpus_db)
    if surface_id == "corpus_builder.embeddings_policy":
        return _embeddings_actions(corpus_db)
    if surface_id == "corpus_builder.search_policy":
        return _search_actions(corpus_db)
    return []


def _settings_actions(corpus_db: str) -> list[dict]:
    rebuild_shared = [_folder("pipeline_root", "Artifact Root", persist_key="artifact_root_path", required=True), _existing_db("corpus_db_path", corpus_db)]
    overrides = [_folder("normalized_dir", "Normalized Dir", advanced=True), _folder("structured_dir", "Structured Dir", advanced=True), _folder("validation_dir", "Validation Dir", advanced=True)]
    rebuild_action = _action(
        "rebuild_from_artifacts",
        "Rebuild Corpus",
        "Bestehende corpus.db aus Artefakten neu aufbauen, optional mit Replace Existing.",
        rebuild_shared + [_checkbox("replace_existing", "Replace Existing", persist_key="replace_existing", default=True)] + overrides,
    )
    _with_rebuild_progress(rebuild_action)
    create_rebuild_action = _new_corpus_db_action(
        "create_and_rebuild_new_corpus_db",
        "Create New Corpus DB",
        "Neue Corpus-DB im Orchestrator-Artefaktordner anlegen, danach aus Artefakten fuellen und als Default-DB einhaengen.",
        [_folder("pipeline_root", "Artifact Root", persist_key="artifact_root_path", required=True)] + overrides,
    )
    _with_rebuild_progress(create_rebuild_action)
    actions = [
        _action("preview_rebuild_from_artifacts", "Rebuild Preview", "Artefaktcluster scannen und den Rebuild vorab pruefen.", rebuild_shared + overrides),
        rebuild_action,
        create_rebuild_action,
    ]
    return actions + _semantic_actions(corpus_db)


def _embeddings_actions(corpus_db: str) -> list[dict]:
    action = _action(
        "generate_embeddings",
        "Generate Embeddings",
        "Offene Embeddings fuer das aktuelle corpus.db ueber die Orchestrator-Runtime berechnen.",
        [_writable_db("corpus_db_path", corpus_db)],
    )
    action["runtime_owner"] = "orchestrator"
    action["orchestrator_action"] = "embeddings"
    action["show_progress_dialog"] = True
    action["progress_title"] = "Generate Embeddings"
    action["progress_status"] = "Embeddings werden fuer die ausgewaehlte Corpus-DB erzeugt."
    return [
        action
    ]


def _with_rebuild_progress(action: dict) -> dict:
    action["show_progress_dialog"] = True
    action["progress_status"] = "Corpus-Rebuild wurde gestartet."
    action["progress_warning"] = (
        "Hinweis: Nach einem Corpus-Rebuild enthaelt die neu aufgebaute DB keine Embeddings. "
        "Starte danach Generate Embeddings, wenn Vektorsuche oder semantische Suche in dieser DB gewuenscht ist."
    )
    return action


def _search_actions(corpus_db: str) -> list[dict]:
    return [
        _action(
            "search",
            "Search Corpus",
            "Volltext-, semantische oder hybride Suche gegen corpus.db ausfuehren.",
            [
                _db("corpus_db_path", corpus_db),
                _text("query", "Query", required=True),
                _select("mode", "Search Mode", ("Fulltext", "Semantisch", "Hybrid"), persist_key="search_mode", default="Fulltext"),
                _number("limit", "Limit", persist_key="search_limit", default=20),
                _text("runtime_model", "Embedding Model", persist_key="search_model", default=_MODEL_DEFAULT, advanced=True),
            ],
        ),
        _action("stats", "Corpus Stats", "Corpus-Statistiken fuer das aktuelle corpus.db anzeigen.", [_db("corpus_db_path", corpus_db)]),
        _action(
            "export",
            "Export Corpus",
            "Corpus als JSONL oder CSV exportieren.",
            [
                _db("corpus_db_path", corpus_db),
                _save("output_path", "Export File", persist_key="export_path", required=True),
                _select("fmt", "Format", ("jsonl", "csv"), persist_key="export_format", default="jsonl"),
                _checkbox("include_archived", "Include Archived", default=False),
            ],
        ),
    ]


def _semantic_actions(corpus_db: str) -> list[dict]:
    return [
        _action("semantic_status", "Semantic Status", "Aktiven, veroeffentlichten und DB-bezogenen Semantic-Status laden.", [_db("corpus_db_path", corpus_db)]),
        _action("load_semantic_release", "Stage Release", "Exportierte JSON-Release-Datei laden und analysieren.", [_file("release_path", "Release Path", required=True), _db("corpus_db_path", corpus_db)]),
        _action(
            "activate_semantic_release",
            "Activate Release",
            "Exportierte JSON-Release-Datei in eine bestehende Corpus-DB laden und sofort aktivieren.",
            [_file("release_path", "Release Path", required=True), _existing_db("corpus_db_path", corpus_db)],
        ),
        _new_corpus_db_action(
            "create_and_activate_new_corpus_db",
            "Create and Activate New Corpus DB",
            "Neue Corpus-DB im Orchestrator-Artefaktordner anlegen, Release dorthin aktivieren und als Default-DB einhaengen.",
            [_file("release_path", "Release Path", required=True)],
        ),
        _action("semantic_audit", "Semantic Audit", "Veroeffentlichten Release gegen DB-Status und Analyse pruefen.", [_db("corpus_db_path", corpus_db)]),
        _action("backfill_stale", "Backfill Stale", "Stale Dokumente mit aktivem Release rematerialisieren.", [_db("corpus_db_path", corpus_db), _number("limit", "Limit", default=100, advanced=True)]),
        _action(
            "merge_preflight",
            "Merge Preflight",
            "Inspect-only Eligibility-Pruefung fuer einen snapshot-first DB-Merge.",
            [_source_db("source_db_path"), _target_db("target_db_path", corpus_db)],
        ),
        _action(
            "merge_corpus_databases",
            "Merge Corpus DBs",
            "Snapshot-first DB-Merge mit interaktivem Risk-Override und globaler Kollisionsentscheidung.",
            [_source_db("source_db_path"), _target_db("target_db_path", corpus_db)],
        ),
    ]


def _action(action: str, label: str, summary: str, inputs: list[dict]) -> dict:
    return {"action": action, "label": label, "summary": summary, "contract_module": _CONTRACT_MODULE, "inputs": inputs}


def _new_corpus_db_action(action: str, label: str, summary: str, inputs: list[dict]) -> dict:
    payload = _action(action, label, summary, inputs)
    payload["new_corpus_db_dialog"] = {
        "title": "Neue Corpus DB erstellen",
        "label_name": "database_label",
        "label_persist_key": "new_corpus_db_label",
        "locale_name": "taxonomy_locale",
        "locale_persist_key": "new_corpus_db_taxonomy_locale",
        "default_locale": "en",
    }
    return payload


def _text(name: str, label: str, *, default: str = "", persist_key: str | None = None, required: bool = False, advanced: bool = False) -> dict:
    return {"name": name, "label": label, "field_type": "text", "default": default, "persist_key": persist_key or name, "required": required, "advanced": advanced}


def _number(name: str, label: str, *, default: int | float, persist_key: str | None = None, advanced: bool = False) -> dict:
    return {"name": name, "label": label, "field_type": "number", "default": default, "persist_key": persist_key or name, "advanced": advanced}


def _checkbox(name: str, label: str, *, default: bool, persist_key: str | None = None) -> dict:
    return {"name": name, "label": label, "field_type": "checkbox", "checkbox_label": label, "default": default, "persist_key": persist_key or name}


def _select(name: str, label: str, values: tuple[str, ...], *, persist_key: str | None = None, default: str) -> dict:
    return {"name": name, "label": label, "field_type": "select", "default": default, "persist_key": persist_key or name, "options": [{"label": value, "value": value} for value in values]}


def _folder(name: str, label: str, *, persist_key: str | None = None, required: bool = False, advanced: bool = False) -> dict:
    return {"name": name, "label": label, "field_type": "open_folder", "persist_key": persist_key or name, "required": required, "advanced": advanced}


def _file(name: str, label: str, *, default: str = "", required: bool = False) -> dict:
    return {"name": name, "label": label, "field_type": "open_file", "default": default, "persist_key": name, "required": required}


def _save(name: str, label: str, *, persist_key: str | None = None, required: bool = False) -> dict:
    return {"name": name, "label": label, "field_type": "save_file", "persist_key": persist_key or name, "required": required}


def _db(name: str, corpus_db: str) -> dict:
    return {"name": name, "label": "Corpus DB Path", "field_type": "open_file", "default": corpus_db, "persist_key": "corpus_db", "required": False}


def _writable_db(name: str, corpus_db: str) -> dict:
    return {"name": name, "label": "Corpus DB Path", "field_type": "save_file", "default": corpus_db, "persist_key": "corpus_db", "required": False}


def _existing_db(name: str, corpus_db: str) -> dict:
    return {"name": name, "label": "Existing Corpus DB Path", "field_type": "open_file", "default": corpus_db, "persist_key": "corpus_db", "required": True}


def _source_db(name: str) -> dict:
    return {"name": name, "label": "Source Corpus DB", "field_type": "open_file", "persist_key": name, "required": True}


def _target_db(name: str, corpus_db: str) -> dict:
    return {"name": name, "label": "Target Corpus DB", "field_type": "open_file", "default": corpus_db, "persist_key": name, "required": True}
