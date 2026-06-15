from __future__ import annotations

import json
from pathlib import Path

from normalizer_vision.models import load_config
from normalizer_vision.normalizer import DocumentNormalizer


def _normalized_output_path(project_root: Path, structured_path: Path) -> Path:
    return project_root / "output" / structured_path.name.replace(".structured.json", ".structured.normalized.json")


def _base_output(*, document_type: str, category: str, subcategory: str, fields: dict, rows: list[dict], free_text: str) -> dict:
    return {
        "schema_version": "1.0",
        "processing": {"model_confidence": 0.95, "needs_review": False, "review_reason": None, "vision_used": False},
        "classification": {"document_type": document_type, "document_type_confidence": 0.95, "category": category, "subcategory": subcategory, "language": "de", "is_scan": True, "has_handwriting": False, "page_count": 1},
        "context": {"company": "envia Mitteldeutsche Energie AG", "document_date": "27.03.2023", "document_title": "Abschlagsplan", "description": "Mitteilung zum Abschlagsplan.", "tags": ["Abschlagsplan"], "people": ["Norman Weiss"], "organizations": ["envia Mitteldeutsche Energie AG"], "locations": ["04668 Grimma"], "date_range": {"from": "01.01.2023", "to": "31.12.2023"}, "currencies": ["EUR"], "recipient_primary": "Norman Weiss", "property_address": "Suedstr. 19, 04668 Grimma", "normalization_notes": []},
        "content": {"structure": {"type": "form_with_table", "columns": [], "form_fields": []}, "fields": fields, "rows": rows, "free_text": free_text},
    }


def test_normalize_payment_schedule_uses_payable_gross_amount_and_derived_structure(tmp_project_root, sample_structured_file, normalizer_runtime_settings):
    payload = _base_output(
        document_type="general_letter",
        category="administrative",
        subcategory="general_correspondence",
        fields={"issuer": "envia", "recipient_primary": "Norman Weiss", "property_address": "Suedstr. 19", "document_number": "ENV 084010019885"},
        rows=[{"_row_type": "payment_schedule", "description": "Abschlagsbetrag", "quantity": "2023-04-23", "unit": "Datum", "unit_price": "40,00 EUR", "line_total": "32,00 EUR", "amount_due": "26,89 EUR", "tenant_share_cost": "-8,00 EUR", "percentage_share": "19 %", "other": "Umsatzsteuer 5,11 EUR", "_units": {"unit_price": "EUR", "line_total": "EUR", "amount_due": "EUR", "tenant_share_cost": "EUR", "percentage_share": "%", "other": "EUR"}}],
        free_text="general_letter recipient: Norman Weiss amount_due: 26,89 EUR",
    )

    class Provider:
        def generate(self, messages, schema, max_output_tokens, thinking_effort) -> str:
            return json.dumps(payload)

        def is_available(self) -> bool:
            return True

        @property
        def provider_name(self) -> str:
            return "openai"

    result = DocumentNormalizer(
        tmp_project_root,
        load_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
        provider=Provider(),
    ).normalize(sample_structured_file, _normalized_output_path(tmp_project_root, sample_structured_file))
    output_data = json.loads(Path(result.output_path).read_text(encoding="utf-8"))
    row = output_data["content"]["rows"][0]
    assert row["amount_due"] == "32,00 EUR"
    assert row["_units"]["percentage_share"] == "%"
    assert "document_number" in output_data["content"]["structure"]["form_fields"]


def test_normalize_hardcodes_known_date_slots_to_iso(tmp_project_root, sample_structured_file, normalizer_runtime_settings):
    payload = _base_output(
        document_type="advance_payment",
        category="finance",
        subcategory="payment_schedule",
        fields={"document_date": "27.03.2023", "period_from": "01.01.2023", "period_to": "31.12.2023"},
        rows=[{"_row_type": "payment_schedule", "scheduled_date": "23.03.2023", "amount_due": "16,00 EUR", "_units": {"amount_due": "EUR"}}],
        free_text="advance_payment document_date: 27.03.2023 scheduled_date: 23.03.2023",
    )

    class Provider:
        def generate(self, messages, schema, max_output_tokens, thinking_effort) -> str:
            return json.dumps(payload)

        def is_available(self) -> bool:
            return True

        @property
        def provider_name(self) -> str:
            return "openai"

    result = DocumentNormalizer(
        tmp_project_root,
        load_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
        provider=Provider(),
    ).normalize(sample_structured_file, _normalized_output_path(tmp_project_root, sample_structured_file))
    output_data = json.loads(Path(result.output_path).read_text(encoding="utf-8"))
    assert output_data["content"]["fields"]["document_date"] == "2023-03-27"
    assert output_data["content"]["fields"]["period_from"] == "2023-01-01"
    assert output_data["content"]["rows"][0]["scheduled_date"] == "2023-03-23"


def test_normalize_preserves_units_and_account_delta_rows(tmp_project_root, sample_structured_file, normalizer_runtime_settings):
    payload = _base_output(
        document_type="authority_notice",
        category="administrative",
        subcategory="official_notice",
        fields={"account_number": "321 812 270", "currency": "EUR"},
        rows=[
            {"_row_type": "consumption_history", "quantity": 102151.48, "amount_due": 596.77, "percentage_share": 1.3, "_units": {"quantity": "Einh./AZ", "amount_due": "EUR", "percentage_share": "%"}},
            {"_row_type": "account_entry", "description": "Rueckstand 12.2014", "scheduled_date": "02.01.2015", "account_delta": -17.98, "_units": {"account_delta": "EUR"}},
        ],
        free_text="authority_notice account_entry account_delta -17.98",
    )

    class Provider:
        def generate(self, messages, schema, max_output_tokens, thinking_effort) -> str:
            return json.dumps(payload)

        def is_available(self) -> bool:
            return True

        @property
        def provider_name(self) -> str:
            return "openai"

    result = DocumentNormalizer(
        tmp_project_root,
        load_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
        provider=Provider(),
    ).normalize(sample_structured_file, _normalized_output_path(tmp_project_root, sample_structured_file))
    output_data = json.loads(Path(result.output_path).read_text(encoding="utf-8"))
    first_row, second_row = output_data["content"]["rows"]
    assert first_row["_units"] == {"quantity": "Einh./AZ", "amount_due": "EUR", "percentage_share": "%"}
    assert second_row["account_delta"] == -17.98
    assert second_row["_units"] == {"account_delta": "EUR"}


def test_normalize_repairs_common_mojibake_in_output_slots(tmp_project_root, sample_structured_file, normalizer_runtime_settings):
    payload = _base_output(
        document_type="advance_payment",
        category="finance",
        subcategory="payment_schedule",
        fields={"property_address": "SÃƒÂ¼dstr. 19, 04668 Grimma", "currency": "Ã¢â€šÂ¬", "other": "Lieferstelle: SÃƒÂ¼dstr. 19; Hinweis fÃƒÂ¼r Kunde"},
        rows=[{"_row_type": "payment_schedule", "description": "Abschlagsplan fÃƒÂ¼r Strompreisbremse", "scheduled_date": "23.03.2023"}],
        free_text="advance_payment Mitteilung fÃƒÆ’Ã‚Â¼r Norman Weiss in WÃƒÆ’Ã‚Â¤hrung ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬",
    )
    payload["context"]["description"] = "Mitteilung zum Abschlagsplan und zur Strompreisbremse fÃƒÂ¼r Norman Weiss."
    payload["context"]["currencies"] = ["Ã¢â€šÂ¬"]

    class Provider:
        def generate(self, messages, schema, max_output_tokens, thinking_effort) -> str:
            return json.dumps(payload)

        def is_available(self) -> bool:
            return True

        @property
        def provider_name(self) -> str:
            return "openai"

    result = DocumentNormalizer(
        tmp_project_root,
        load_config(tmp_project_root),
        runtime_settings=normalizer_runtime_settings,
        provider=Provider(),
    ).normalize(sample_structured_file, _normalized_output_path(tmp_project_root, sample_structured_file))
    output_data = json.loads(Path(result.output_path).read_text(encoding="utf-8"))
    assert output_data["content"]["fields"]["currency"] != "Ã¢â€šÂ¬"
    assert output_data["content"]["rows"][0]["description"].startswith("Abschlagsplan")
    assert "fÃƒÂ¼r" not in output_data["content"]["rows"][0]["description"]
    assert "fÃƒÂ¼r" not in output_data["content"]["free_text"]
