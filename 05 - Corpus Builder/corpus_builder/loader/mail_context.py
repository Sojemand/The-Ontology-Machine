"""Mail-context persistence and derived relation sync for loader workflow."""

from __future__ import annotations

import sqlite3

from . import policy, repository
from .types import JsonDict

MAIL_CONTEXT_FIELD_KEYS = (
    "mail_id",
    "mail_scope",
    "mail_sender",
    "mail_sender_address",
    "mail_split_mode",
    "attachment_id",
    "attachment_name",
    "attachment_page_ref",
    "attachment_status",
)


def insert_mail_context_fields(conn: sqlite3.Connection, document_id: str, prepared) -> JsonDict:
    context_fields: JsonDict = {}
    for key in MAIL_CONTEXT_FIELD_KEYS:
        value = _preferred_context_value(prepared, key)
        if not policy.is_non_empty(value):
            continue
        context_fields[key] = value
        repository.insert_field(conn, document_id, key, value, source=f"context.{key}")
    return context_fields


def sync_mail_relations(conn: sqlite3.Connection, document_id: str, mail_context: JsonDict) -> None:
    mail_id = str(mail_context.get("mail_id") or "").strip()
    mail_scope = str(mail_context.get("mail_scope") or "").strip()
    if not mail_id or mail_scope not in {"body", "attachment"}:
        return
    if mail_scope == "body":
        for attachment_id in _mail_counterpart_ids(conn, mail_id=mail_id, scope="attachment", exclude_document_id=document_id):
            hint = _attachment_hint(conn, attachment_id)
            _replace_document_relation(conn, document_id=document_id, relation_type="mail_attachment", target_document_id=attachment_id, target_hint=hint, description=f"Attachment linked via mail_id={mail_id}")
            _replace_document_relation(conn, document_id=attachment_id, relation_type="mail_body", target_document_id=document_id, target_hint=document_id, description=f"Mail body linked via mail_id={mail_id}")
        return
    attachment_hint = str(mail_context.get("attachment_name") or document_id)
    for body_id in _mail_counterpart_ids(conn, mail_id=mail_id, scope="body", exclude_document_id=document_id):
        _replace_document_relation(conn, document_id=body_id, relation_type="mail_attachment", target_document_id=document_id, target_hint=attachment_hint, description=f"Attachment linked via mail_id={mail_id}")
        _replace_document_relation(conn, document_id=document_id, relation_type="mail_body", target_document_id=body_id, target_hint=body_id, description=f"Mail body linked via mail_id={mail_id}")


def _preferred_context_value(prepared, key: str):
    preferred = _context_mapping(prepared.preferred_json)
    if policy.is_non_empty(preferred.get(key)):
        return preferred.get(key)
    structured = _context_mapping(prepared.structured_payload)
    return structured.get(key)


def _context_mapping(payload: JsonDict) -> JsonDict:
    context = payload.get("context")
    return context if isinstance(context, dict) else {}


def _mail_counterpart_ids(conn: sqlite3.Connection, *, mail_id: str, scope: str, exclude_document_id: str) -> list[str]:
    rows = conn.execute(
        """
        SELECT d.id
        FROM documents d
        JOIN extracted_fields mail_id_field
          ON mail_id_field.document_id = d.id
         AND mail_id_field.key = 'mail_id'
         AND mail_id_field.value = ?
        JOIN extracted_fields mail_scope_field
          ON mail_scope_field.document_id = d.id
         AND mail_scope_field.key = 'mail_scope'
         AND mail_scope_field.value = ?
        WHERE d.is_archived = 0
          AND d.id <> ?
        ORDER BY d.id
        """,
        (mail_id, scope, exclude_document_id),
    ).fetchall()
    return [str(row["id"]) for row in rows]


def _attachment_hint(conn: sqlite3.Connection, attachment_id: str) -> str:
    row = conn.execute(
        "SELECT value FROM extracted_fields WHERE document_id = ? AND key = 'attachment_name' ORDER BY id DESC LIMIT 1",
        (attachment_id,),
    ).fetchone()
    return str((row["value"] if row else None) or attachment_id)


def _replace_document_relation(
    conn: sqlite3.Connection,
    *,
    document_id: str,
    relation_type: str,
    target_document_id: str,
    target_hint: str,
    description: str,
) -> None:
    conn.execute(
        "DELETE FROM relations WHERE document_id = ? AND relation_type = ? AND target_document_id = ?",
        (document_id, relation_type, target_document_id),
    )
    repository.insert_relation(
        conn,
        document_id,
        {
            "type": relation_type,
            "target_document_id": target_document_id,
            "target_hint": target_hint,
            "description": description,
            "relation_origin": "derived",
            "status": "derived",
            "created_by": "corpus_builder",
            "evidence_refs": [f"context.mail_id:{target_hint}"],
        },
    )
