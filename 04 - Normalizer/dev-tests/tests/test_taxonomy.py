from __future__ import annotations

import pytest

from normalizer_vision.assets import load_local_profile
from normalizer_vision.taxonomy import (
    projection_payload_from_domains,
    projection_payload_from_template,
)
from normalizer_vision.taxonomy_compile import ensure_compiled_taxonomy_assets

CORE_PROJECTION_SAMPLES = [
    ("housing.default.v1", "utility_cost_statement", "advance_payment_adjustment", "issuer", "scheduled_date"),
    ("operations.default.v1", "delivery_note", "execution_plan", "our_reference", "position"),
    ("finance.default.v1", "statement", "payroll_accounting", "cost_center", "rate"),
    ("technical.default.v1", "specification", "asset_documentation", "asset_id", "identifier"),
    ("legal.public_admin.default.v1", "authority_notice", "permit_license", "authority_name", "status"),
    ("people.identity.default.v1", "profile", "identity_record", "personal_id_number", "hours"),
    ("health.care.default.v1", "prescription", "medication", "patient_name", "dosage"),
    ("personal.wellbeing.default.v1", "schedule", "habit_tracking", "appointment_date", "frequency"),
    ("community.spiritual.default.v1", "membership_record", "membership", "membership_id", "identifier"),
    ("business.customer.communication.default.v1", "general_letter", "business_correspondence", "customer_number", "status"),
]


def _compiled_assets(tmp_project_root):
    compiled = ensure_compiled_taxonomy_assets(tmp_project_root)
    assert compiled is not None
    return compiled


def test_projection_loads_against_master(tmp_project_root):
    compiled = _compiled_assets(tmp_project_root)
    profile = load_local_profile(tmp_project_root, "housing.default.v1")
    referenced_promotion_slots = {
        rule["slot"]
        for rule in profile.promotion_rules
        if isinstance(rule, dict) and rule.get("slot")
    }

    assert compiled.master["taxonomy_id"] == "normalizer_taxonomy.master"
    assert profile.projection_id == "housing.default.v1"
    assert "utility_cost_statement" in profile.document_types
    assert "advance_payment" in profile.document_types
    assert "advance_payment_adjustment" in profile.subcategories
    assert "issuer" in profile.field_codes
    assert "recipient_address" in profile.field_codes
    assert "subject" in profile.field_codes
    assert "bank_name" in profile.field_codes
    assert "cost_breakdown_history" in profile.row_types
    assert "payment_schedule" in profile.subcategories
    assert "scheduled_date" in profile.cell_codes
    assert "average_building_usage" in profile.cell_codes
    assert "average_tenant_usage" in profile.cell_codes
    assert "usage_unit" in profile.cell_codes
    assert "average_usage_unit" in profile.cell_codes
    assert "account_delta" in profile.cell_codes
    assert {slot["slot"] for slot in profile.promotion_slots} == referenced_promotion_slots


def test_projection_payload_from_template(tmp_project_root):
    master = _compiled_assets(tmp_project_root).master
    payload = projection_payload_from_template(master, "housing.default.v1")
    assert payload["projection_id"] == "housing.default.v1"
    assert payload["routing"]["when_to_use"].startswith("Housing, utility, tenancy")
    assert "utility_cost_statement" in payload["include_document_types"]
    assert "advance_payment_adjustment" in payload["include_subcategories"]
    assert "recipient_address" in payload["include_field_codes"]


def test_projection_payload_from_domains_includes_other(tmp_project_root):
    master = _compiled_assets(tmp_project_root).master
    payload = projection_payload_from_domains(
        master,
        projection_id="finance.only.v1",
        label="Finance Only v1",
        domain_ids=["finance"],
    )
    assert payload["projection_id"] == "finance.only.v1"
    assert "invoice" in payload["include_document_types"]
    assert "other" in payload["include_document_types"]
    assert "finance" in payload["include_categories"]


def test_operations_projection_loads_against_master(tmp_project_root):
    profile = load_local_profile(tmp_project_root, "operations.default.v1")

    assert profile.projection_id == "operations.default.v1"
    assert "delivery_note" in profile.document_types
    assert "specification" in profile.document_types
    assert "operations" in profile.categories
    assert "personal" in profile.categories
    assert "execution_plan" in profile.subcategories
    assert "technical_specification" in profile.subcategories
    assert "our_reference" in profile.field_codes
    assert "carrier_name" in profile.field_codes
    assert "line_item" in profile.row_types
    assert "position" in profile.cell_codes
    assert "participant_role" in profile.cell_codes

    assert profile.canonical_code("document_type", "letter", "other") == "general_letter"
    assert profile.canonical_code("category", "administration", "other") == "administrative"
    assert profile.canonical_code("subcategory", "deployment plan", "other") == "execution_plan"
    assert profile.canonical_code("subcategory", "inventory list", "other") == "inventory"
    assert profile.canonical_code("subcategory", "transport order delivery note", "other") == "logistics"
    assert profile.canonical_code("field", "our reference", None) == "our_reference"
    assert profile.canonical_code("field", "vehicle registration", None) == "vehicle_registration"
    assert profile.canonical_code("cell", "date", None) == "scheduled_date"
    assert profile.canonical_code("cell", "description", None) == "description"
    assert profile.canonical_code("cell", "participant role", None) == "participant_role"


def test_projection_payload_from_operations_template(tmp_project_root):
    master = _compiled_assets(tmp_project_root).master
    payload = projection_payload_from_template(master, "operations.default.v1")

    assert payload["projection_id"] == "operations.default.v1"
    assert payload["routing"]["avoid_when"].startswith("Not for tenancy, utility charges")
    assert "delivery_note" in payload["include_document_types"]
    assert "operations" in payload["include_categories"]
    assert "execution_plan" in payload["include_subcategories"]
    assert "our_reference" in payload["include_field_codes"]
    assert "position" in payload["include_cell_codes"]


@pytest.mark.parametrize(
    ("projection_id", "document_type", "subcategory", "field_code", "cell_code"),
    CORE_PROJECTION_SAMPLES,
)
def test_all_core_projections_load_against_master(
    tmp_project_root,
    projection_id,
    document_type,
    subcategory,
    field_code,
    cell_code,
):
    profile = load_local_profile(tmp_project_root, projection_id)

    assert profile.projection_id == projection_id
    assert profile.master_taxonomy_version == "2026-03-28.v6"
    assert document_type in profile.document_types
    assert subcategory in profile.subcategories
    assert field_code in profile.field_codes
    assert cell_code in profile.cell_codes


@pytest.mark.parametrize("projection_id", [sample[0] for sample in CORE_PROJECTION_SAMPLES])
def test_projection_payload_from_all_templates(tmp_project_root, projection_id):
    master = _compiled_assets(tmp_project_root).master
    payload = projection_payload_from_template(master, projection_id)

    assert payload["projection_id"] == projection_id
    assert payload["master_taxonomy_version"] == "2026-03-28.v6"
    assert payload["routing"]["when_to_use"]
    assert payload["routing"]["avoid_when"]
    assert payload["routing"]["example_document_types"]
    assert payload["routing"]["surface_signals"]["text_markers"]


@pytest.mark.parametrize("projection_id", [sample[0] for sample in CORE_PROJECTION_SAMPLES])
def test_compiled_projection_payloads_expose_routing_block(tmp_project_root, projection_id):
    payload = _compiled_assets(tmp_project_root).projections[projection_id]

    assert payload["routing"]["when_to_use"]
    assert payload["routing"]["avoid_when"]
    assert payload["routing"]["example_document_types"]
    assert payload["routing"]["surface_signals"]["domain_markers"]
