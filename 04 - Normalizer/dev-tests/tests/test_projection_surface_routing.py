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

CONFLICT_CASES = [
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
                    "customer_number": "KD-22",
                    "contract_number": "VT-88",
                    "department_name": "Customer service",
                },
                "rows": [{"_row_type": "contact_block", "description": "Service contact", "status": "active"}],
                "free_text": (
                    "Welcome to customer service. Customer number KD-22, contract number VT-88, "
                    "mail forwarding active and phone number updated."
                ),
            },
        },
        "text_marker:customer service",
    ),
    (
        "legal.public_admin.default.v1",
        {
            "classification": {"document_type": "payment_notice", "category": "administrative", "subcategory": "payment_followup"},
            "content": {
                "fields": {"authority_name": "Stadt Leipzig", "case_id": "AZ-44", "document_number": "K-77"},
                "rows": [{"_row_type": "line_item", "description": "Arrears from notice amount", "balance": "420.00 EUR"}],
                "free_text": "Authority reminder for payment tracking. Case reference AZ-44, treasury reference K-77, open arrears.",
            },
        },
        "text_marker:case reference",
    ),
    (
        "finance.default.v1",
        {
            "classification": {"document_type": "payment_notice", "category": "finance", "subcategory": "payment_followup"},
            "content": {
                "fields": {"invoice_number": "INV-1007", "customer_name": "Acme GmbH", "iban": "DE0210010010", "bic": "BELADEBEXXX"},
                "rows": [{"_row_type": "account_entry", "description": "Outstanding amount", "amount_due": "1200.00 EUR"}],
                "free_text": "Payment reminder for invoice INV-1007 with due date 2026-04-10. Customer Acme GmbH, outstanding amount 1200 EUR.",
            },
        },
        "text_marker:invoice",
    ),
    (
        "housing.default.v1",
        {
            "classification": {"document_type": "payment_notice", "category": "finance", "subcategory": "payment_followup"},
            "content": {
                "fields": {
                    "tenant_name": "Mara Beispiel",
                    "property_manager_name": "Hausverwaltung Nord",
                    "property_address": "Bonhoefferstr. 15",
                },
                "rows": [{"_row_type": "account_entry", "description": "Heating cost arrears", "balance": "275.00 EUR"}],
                "free_text": "Reminder for the apartment at Bonhoefferstr. 15. Tenant Mara Beispiel has open heating costs and utility costs.",
            },
        },
        "text_marker:apartment",
    ),
]


def test_surface_signal_routing_separates_conflict_profiles(tmp_project_root):
    profiles = {
        projection_id: load_local_profile(tmp_project_root, projection_id)
        for projection_id in CORE_PROJECTION_IDS
    }

    for expected_projection_id, raw_doc, expected_signal in CONFLICT_CASES:
        scores = {
            projection_id: score_profile(profile, raw_doc)
            for projection_id, profile in profiles.items()
        }
        ranked = sorted(scores.items(), key=lambda item: (-item[1][0], item[0]))

        assert ranked[0][0] == expected_projection_id
        assert ranked[0][1][0] > ranked[1][1][0]
        assert expected_signal in scores[expected_projection_id][1]
