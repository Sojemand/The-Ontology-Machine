from __future__ import annotations

import json

from tests.fixtures.loader_io import load_input_file

def test_load_from_file_materializes_mail_context_and_links_body_attachment(db, make_input_pair):
    report = {"result": "pass", "summary": {"total_issues": 0}, "issues": []}
    body_structured = {
        "schema_version": "1.0",
        "source": {"file_name": "mail_case.msg", "file_path": "mail_case.msg::page=001-of-002"},
        "processing": {"model": "test-model", "model_confidence": 0.98, "needs_review": False, "vision_used": False},
        "classification": {"document_type": "email", "category": "communication", "subcategory": "business_email", "language": "de", "page_count": 2},
        "context": {
            "document_title": "Subject: Test Mail",
            "document_date": "Date: 2023-05-15 09:43:48+02:00",
            "page_number": 1,
            "document_page_count": 2,
            "mail_id": "mail_123",
            "mail_scope": "body",
            "mail_sender": "Petra Wiesner",
            "mail_sender_address": "petra@example.com",
            "mail_split_mode": "exact",
        },
        "content": {
            "fields": {
                "from": 'From: "Petra Wiesner" <petra@example.com>',
                "to": 'To: "Andreas Wiesner" <andreas@example.com>',
                "subject": "Subject: Test Mail",
                "date": "Date: 2023-05-15 09:43:48+02:00",
            },
            "rows": [],
            "segments": [
                {
                    "segment_id": "Page1_Segment1",
                    "unit_kind": "message_paragraph",
                    "function": "sending_invoice_notice",
                    "page": 1,
                    "sequence": 1,
                    "text": "Im Anhang die Rechnung.",
                }
            ],
            "free_text": "Im Anhang die Rechnung.",
        },
    }
    body_normalized = {
        "schema_version": "1.0",
        "source": {"file_name": "mail_case.msg", "file_path": "mail_case.msg::page=001-of-002"},
        "processing": {"model": "test-model", "model_confidence": 0.98, "needs_review": False, "vision_used": False},
        "classification": {"document_type": "general_letter", "category": "business", "subcategory": "business_correspondence", "language": "de", "page_count": 2},
        "context": {"document_title": "Test Mail", "document_date": "2023-05-15", "taxonomy_profile_id": "business.customer.communication.default.v1"},
        "content": {
            "fields": {"sender": "Petra Wiesner", "recipient": "Andreas Wiesner", "subject": "Test Mail", "document_date": "2023-05-15"},
            "rows": [],
            "free_text": "general_letter sender=Petra recipient=Andreas subject=Test Mail",
        },
        "projection": {"projection_id": "business.customer.communication.default.v1"},
    }
    attachment_structured = {
        "schema_version": "1.0",
        "source": {"file_name": "mail_case.msg", "file_path": "mail_case.msg::page=002-of-002"},
        "processing": {"model": "test-model", "model_confidence": 0.98, "needs_review": False, "vision_used": False},
        "classification": {"document_type": "invoice", "category": "finance", "subcategory": "rechnung", "language": "de", "page_count": 2},
        "context": {
            "page_number": 2,
            "document_page_count": 2,
            "mail_id": "mail_123",
            "mail_scope": "attachment",
            "attachment_id": "att_001",
            "attachment_name": "invoice.pdf",
            "attachment_page_ref": "p001-of-001",
            "attachment_status": "ok",
            "document_date": "08.05.2023",
        },
        "content": {
            "fields": {"invoice_number": "3.043", "invoice_date": "08.05.2023", "total_amount": "520,00 EUR"},
            "rows": [],
            "segments": [],
            "free_text": "Rechnung 3.043",
        },
    }
    attachment_normalized = {
        "schema_version": "1.0",
        "source": {"file_name": "mail_case.msg", "file_path": "mail_case.msg::page=002-of-002"},
        "processing": {"model": "test-model", "model_confidence": 0.98, "needs_review": False, "vision_used": False},
        "classification": {"document_type": "invoice", "category": "finance", "subcategory": "accounts_receivable", "language": "de", "page_count": 2},
        "context": {"document_title": "Rechnung Nr. 3.043", "document_date": "2023-05-08", "taxonomy_profile_id": "finance.default.v1"},
        "content": {
            "fields": {"invoice_number": "3.043", "document_date": "2023-05-08", "total_amount": 520},
            "rows": [],
            "free_text": "invoice 3.043 total 520 EUR",
        },
        "projection": {"projection_id": "finance.default.v1"},
    }

    attachment_path = make_input_pair(
        "mail_case.msg.p002.of002",
        attachment_structured,
        vision_report=report,
        normalized=attachment_normalized,
    )
    body_path = make_input_pair(
        "mail_case.msg.p001.of002",
        body_structured,
        vision_report=report,
        normalized=body_normalized,
    )

    assert load_input_file(db, attachment_path).status == "loaded"
    assert load_input_file(db, body_path).status == "loaded"

    source_rows = db.execute(
        "SELECT id, file_path, source_file_path, source_page, source_page_count, "
        "source_document_id, source_uri, source_artifact_id, page_index, materialization_order "
        "FROM documents WHERE id IN (?, ?) ORDER BY id",
        ("mail_case.msg.p001.of002", "mail_case.msg.p002.of002"),
    ).fetchall()
    assert [dict(row) for row in source_rows] == [
        {
            "id": "mail_case.msg.p001.of002",
            "file_path": "mail_case.msg::page=001-of-002",
            "source_file_path": "mail_case.msg",
            "source_page": 1,
            "source_page_count": 2,
            "source_document_id": "mail_case.msg",
            "source_uri": "mail_case.msg",
            "source_artifact_id": "mail_case.msg",
            "page_index": 0,
            "materialization_order": 0,
        },
        {
            "id": "mail_case.msg.p002.of002",
            "file_path": "mail_case.msg::page=002-of-002",
            "source_file_path": "mail_case.msg",
            "source_page": 2,
            "source_page_count": 2,
            "source_document_id": "mail_case.msg",
            "source_uri": "mail_case.msg",
            "source_artifact_id": "mail_case.msg",
            "page_index": 1,
            "materialization_order": 1,
        },
    ]

    field_rows = db.execute(
        "SELECT document_id, key, value FROM extracted_fields WHERE document_id IN (?, ?) AND key IN ('mail_id','mail_scope','mail_sender','mail_sender_address','attachment_id','attachment_name') ORDER BY document_id, key",
        ("mail_case.msg.p001.of002", "mail_case.msg.p002.of002"),
    ).fetchall()
    assert [dict(row) for row in field_rows] == [
        {"document_id": "mail_case.msg.p001.of002", "key": "mail_id", "value": "mail_123"},
        {"document_id": "mail_case.msg.p001.of002", "key": "mail_scope", "value": "body"},
        {"document_id": "mail_case.msg.p001.of002", "key": "mail_sender", "value": "Petra Wiesner"},
        {"document_id": "mail_case.msg.p001.of002", "key": "mail_sender_address", "value": "petra@example.com"},
        {"document_id": "mail_case.msg.p002.of002", "key": "attachment_id", "value": "att_001"},
        {"document_id": "mail_case.msg.p002.of002", "key": "attachment_name", "value": "invoice.pdf"},
        {"document_id": "mail_case.msg.p002.of002", "key": "mail_id", "value": "mail_123"},
        {"document_id": "mail_case.msg.p002.of002", "key": "mail_scope", "value": "attachment"},
    ]

    relation_rows = db.execute(
        "SELECT document_id, relation_type, target_document_id, target_hint, relation_origin FROM relations ORDER BY document_id, relation_type",
    ).fetchall()
    assert [dict(row) for row in relation_rows] == [
        {
            "document_id": "mail_case.msg.p001.of002",
            "relation_type": "mail_attachment",
            "target_document_id": "mail_case.msg.p002.of002",
            "target_hint": "invoice.pdf",
            "relation_origin": "derived",
        },
        {
            "document_id": "mail_case.msg.p002.of002",
            "relation_type": "mail_body",
            "target_document_id": "mail_case.msg.p001.of002",
            "target_hint": "mail_case.msg.p001.of002",
            "relation_origin": "derived",
        },
    ]

    reloaded_body = json.loads(json.dumps(body_normalized))
    reloaded_body["content"]["fields"]["subject"] = "Test Mail Reloaded"
    reloaded_body["content"]["free_text"] = "general_letter sender=Petra recipient=Andreas subject=Test Mail Reloaded"
    body_path = make_input_pair(
        "mail_case.msg.p001.of002",
        body_structured,
        vision_report=report,
        normalized=reloaded_body,
    )
    assert load_input_file(db, body_path).status in {"loaded", "archived_and_loaded"}
    assert db.execute("SELECT COUNT(*) FROM relations").fetchone()[0] == 2
