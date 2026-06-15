from __future__ import annotations

from normalizer_vision.assets import load_local_profile
from normalizer_vision.projection_routing.policy import score_profile

CORE_PROJECTION_IDS = [
    "community.spiritual.default.v1",
    "business.customer.communication.default.v1",
    "finance.default.v1",
    "health.care.default.v1",
    "housing.default.v1",
    "legal.public_admin.default.v1",
    "operations.default.v1",
    "people.identity.default.v1",
    "personal.wellbeing.default.v1",
    "technical.default.v1",
]

ROUTING_CASES = [
    (
        "business.customer.communication.default.v1",
        {
            "classification": {
                "document_type": "general_letter",
                "category": "business",
                "subcategory": "business_correspondence",
            },
            "content": {
                "fields": {
                    "customer_number": "KD-99",
                    "contract_number": "VT-77",
                    "account_number": "AC-11",
                    "phone": "0170123456",
                    "subject": "Welcome to ExampleTel",
                },
                "structure": {"form_fields": ["customer_number", "contract_number"], "columns": ["description", "status"]},
                "rows": [{"_row_type": "contact_block", "description": "Customer service", "status": "active"}],
                "free_text": (
                    "Welcome to customer service. Customer number KD-99, contract number VT-77, "
                    "customer account AC-11 and phone number 0170123456 are recorded."
                ),
            },
        },
    ),
    (
        "finance.default.v1",
        {
            "classification": {"document_type": "statement", "category": "finance", "subcategory": "payroll_accounting"},
            "content": {
                "fields": {"cost_center": "CC-44", "employee_id": "E-17"},
                "structure": {"form_fields": ["cost_center"], "columns": ["rate", "hours"]},
                "rows": [{"_row_type": "account_entry", "rate": "32.5", "hours": "40"}],
            },
        },
    ),
    (
        "technical.default.v1",
        {
            "classification": {"document_type": "specification", "category": "technical", "subcategory": "asset_documentation"},
            "content": {
                "fields": {"asset_id": "AS-77", "serial_number": "SN-5", "site_name": "Plant North"},
                "structure": {"form_fields": ["asset_id"], "columns": ["identifier", "status"]},
                "rows": [{"_row_type": "line_item", "identifier": "Valve-22", "status": "approved"}],
            },
        },
    ),
    (
        "legal.public_admin.default.v1",
        {
            "classification": {"document_type": "authority_notice", "category": "legal", "subcategory": "permit_license"},
            "content": {
                "fields": {"permit_number": "PL-9", "authority_name": "City of Leipzig", "personal_id_number": "ID-88"},
                "structure": {"form_fields": ["permit_number"], "columns": ["identifier", "status"]},
                "rows": [{"_row_type": "timeline_entry", "identifier": "PL-9", "status": "granted"}],
            },
        },
    ),
    (
        "people.identity.default.v1",
        {
            "classification": {"document_type": "profile", "category": "people", "subcategory": "identity_record"},
            "content": {
                "fields": {"employee_id": "MA-77", "date_of_birth": "1990-01-01", "personal_id_number": "P-123"},
                "structure": {"form_fields": ["employee_id"], "columns": ["hours", "rate"]},
                "rows": [{"_row_type": "participant_list", "hours": "40", "rate": "1.0"}],
            },
        },
    ),
    (
        "health.care.default.v1",
        {
            "classification": {"document_type": "prescription", "category": "health", "subcategory": "medication"},
            "content": {
                "fields": {"patient_name": "Erika Muster", "insurance_number": "KV-22", "medication_name": "Ibuprofen"},
                "structure": {"form_fields": ["patient_name"], "columns": ["dosage", "frequency"]},
                "rows": [{"_row_type": "line_item", "dosage": "1", "frequency": "twice daily"}],
            },
        },
    ),
    (
        "personal.wellbeing.default.v1",
        {
            "classification": {"document_type": "schedule", "category": "personal", "subcategory": "habit_tracking"},
            "content": {
                "fields": {"person_name": "Erika Muster", "appointment_date": "2026-03-28", "provider_name": "Coach M"},
                "structure": {"form_fields": ["person_name"], "columns": ["frequency", "hours", "status"]},
                "rows": [{"_row_type": "timeline_entry", "frequency": "daily", "hours": "1", "status": "stable"}],
            },
        },
    ),
    (
        "community.spiritual.default.v1",
        {
            "classification": {"document_type": "membership_record", "category": "community", "subcategory": "membership"},
            "content": {
                "fields": {"membership_id": "M-12", "community_name": "Sunshine Association", "event_name": "Spring Festival"},
                "structure": {"form_fields": ["membership_id"], "columns": ["identifier", "status"]},
                "rows": [{"_row_type": "participant_list", "identifier": "P-1", "status": "active"}],
            },
        },
    ),
]


def test_new_projection_routing_cases_score_highest(tmp_project_root):
    profiles = {
        projection_id: load_local_profile(tmp_project_root, projection_id)
        for projection_id in CORE_PROJECTION_IDS
    }

    for expected_projection_id, raw_doc in ROUTING_CASES:
        scores = {
            projection_id: score_profile(profile, raw_doc)[0]
            for projection_id, profile in profiles.items()
        }
        top_score = max(scores.values())
        second_score = sorted(scores.values(), reverse=True)[1]

        assert scores[expected_projection_id] == top_score
        assert scores[expected_projection_id] > second_score


def test_core_projection_routing_lexicon_is_english_control_language(tmp_project_root):
    checks = {
        "finance.default.v1": {"required": {"invoice", "payment terms"}, "forbidden": {"rechnung", "zahlungsziel"}},
        "housing.default.v1": {"required": {"apartment", "utility costs"}, "forbidden": {"wohnung", "betriebskosten"}},
        "legal.public_admin.default.v1": {"required": {"notice", "case reference"}, "forbidden": {"bescheid", "aktenzeichen"}},
        "operations.default.v1": {"required": {"transport order", "deployment plan"}, "forbidden": {"transportauftrag", "einsatzplan"}},
    }

    for projection_id, expectation in checks.items():
        profile = load_local_profile(tmp_project_root, projection_id)
        text_markers = set(profile.surface_signals["text_markers"])
        domain_markers = {
            marker
            for markers in profile.surface_signals["domain_markers"].values()
            for marker in markers
        }
        all_markers = text_markers | domain_markers

        assert expectation["required"] <= all_markers
        assert expectation["forbidden"].isdisjoint(all_markers)
