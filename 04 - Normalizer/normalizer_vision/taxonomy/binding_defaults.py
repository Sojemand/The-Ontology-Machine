"""Semantic binding defaults for master taxonomy sections."""
from __future__ import annotations

from typing import Any

_FIELD_BINDINGS: dict[str, dict[str, Any]] = {
    "issuer": {"entity_type": "party", "role_type": "issuer", "attribute_code": "name"},
    "sender": {"entity_type": "party", "role_type": "sender", "attribute_code": "name"},
    "sender_address": {"entity_type": "address", "role_type": "sender", "attribute_code": "address_text"},
    "recipient": {"entity_type": "party", "role_type": "recipient", "attribute_code": "name"},
    "recipient_address": {"entity_type": "address", "role_type": "recipient", "attribute_code": "address_text"},
    "recipient_primary": {"entity_type": "party", "role_type": "recipient_primary", "attribute_code": "name"},
    "customer_name": {"entity_type": "party", "role_type": "customer", "attribute_code": "name"},
    "tenant_name": {"entity_type": "party", "role_type": "tenant", "attribute_code": "name"},
    "owner_name": {"entity_type": "party", "role_type": "owner", "attribute_code": "name"},
    "property_manager_name": {"entity_type": "party", "role_type": "property_manager", "attribute_code": "name"},
    "property_address": {"entity_type": "property", "role_type": "property_address", "attribute_code": "address_text"},
    "property_manager_internal_id": {"entity_type": "identifier", "role_type": "property_manager", "attribute_code": "identifier_value", "identifier_family": "property_manager_internal_id"},
    "document_number": {"entity_type": "identifier", "attribute_code": "identifier_value", "identifier_family": "document_number"},
    "our_reference": {"entity_type": "identifier", "role_type": "our_reference", "attribute_code": "identifier_value", "identifier_family": "our_reference"},
    "your_reference": {"entity_type": "identifier", "role_type": "your_reference", "attribute_code": "identifier_value", "identifier_family": "your_reference"},
    "subject": {"entity_type": "document_fact", "attribute_code": "subject"},
    "salutation": {"entity_type": "document_fact", "attribute_code": "salutation"},
    "closing": {"entity_type": "document_fact", "attribute_code": "closing"},
    "invoice_number": {"entity_type": "identifier", "attribute_code": "identifier_value", "identifier_family": "invoice_number"},
    "contract_number": {"entity_type": "identifier", "attribute_code": "identifier_value", "identifier_family": "contract_number"},
    "account_number": {"entity_type": "identifier", "attribute_code": "identifier_value", "identifier_family": "account_number"},
    "document_date": {"entity_type": "document_fact", "attribute_code": "document_date"},
    "period_from": {"entity_type": "period", "attribute_code": "from"},
    "period_to": {"entity_type": "period", "attribute_code": "to"},
    "due_date": {"entity_type": "document_fact", "attribute_code": "due_date"},
    "currency": {"entity_type": "document_fact", "attribute_code": "currency"},
    "reference_amount": {"entity_type": "financial_amount", "attribute_code": "reference_amount"},
    "total_amount": {"entity_type": "financial_amount", "attribute_code": "total_amount"},
    "net_amount": {"entity_type": "financial_amount", "attribute_code": "net_amount"},
    "tax_amount": {"entity_type": "financial_amount", "attribute_code": "tax_amount"},
    "balance_amount": {"entity_type": "financial_amount", "attribute_code": "balance_amount"},
    "bank_name": {"entity_type": "document_fact", "attribute_code": "bank_name"},
    "iban": {"entity_type": "identifier", "attribute_code": "identifier_value", "identifier_family": "iban"},
    "bic": {"entity_type": "identifier", "attribute_code": "identifier_value", "identifier_family": "bic"},
    "phone": {"entity_type": "document_fact", "attribute_code": "phone"},
    "contact_person": {"entity_type": "party", "role_type": "contact_person", "attribute_code": "name"},
    "carrier_name": {"entity_type": "party", "role_type": "carrier", "attribute_code": "name"},
    "vehicle_registration": {"entity_type": "identifier", "role_type": "vehicle_registration", "attribute_code": "identifier_value", "identifier_family": "vehicle_registration"},
    "loading_address": {"entity_type": "address", "role_type": "loading", "attribute_code": "address_text"},
    "transfer_address": {"entity_type": "address", "role_type": "transfer", "attribute_code": "address_text"},
    "unloading_address": {"entity_type": "address", "role_type": "unloading", "attribute_code": "address_text"},
    "register_court": {"entity_type": "document_fact", "attribute_code": "register_court"},
    "commercial_register": {"entity_type": "identifier", "attribute_code": "identifier_value", "identifier_family": "commercial_register"},
    "tax_id": {"entity_type": "identifier", "attribute_code": "identifier_value", "identifier_family": "tax_id"},
    "page_indicator": {"entity_type": "document_fact", "attribute_code": "page_indicator"},
    "meter_id": {"entity_type": "identifier", "attribute_code": "identifier_value", "identifier_family": "meter_id"},
    "case_id": {"entity_type": "identifier", "attribute_code": "identifier_value", "identifier_family": "case_id"},
}

_ROW_BINDINGS: dict[str, dict[str, Any]] = {
    "line_item": {"entity_type": "line_item", "role_type": "line_item", "materialize_each_row": True},
    "cost_breakdown_current": {"entity_type": "line_item", "role_type": "cost_breakdown_current", "materialize_each_row": True},
    "cost_breakdown_history": {"entity_type": "line_item", "role_type": "cost_breakdown_history", "materialize_each_row": True},
    "consumption_current": {"entity_type": "measurement", "role_type": "measurement_entry", "materialize_each_row": True},
    "consumption_history": {"entity_type": "measurement", "role_type": "measurement_entry", "materialize_each_row": True},
    "payment_schedule": {"entity_type": "event", "role_type": "schedule_entry", "materialize_each_row": True},
    "account_entry": {"entity_type": "event", "role_type": "account_entry", "materialize_each_row": True},
    "meter_reading_series": {"entity_type": "measurement", "role_type": "measurement_entry", "materialize_each_row": True},
    "participant_list": {"entity_type": "party", "role_type": "participant_list", "materialize_each_row": True},
    "contact_block": {"entity_type": "document_fact", "role_type": "contact_block", "materialize_each_row": True},
    "timeline_entry": {"entity_type": "event", "role_type": "timeline_entry", "materialize_each_row": True},
}

_CELL_BINDINGS: dict[str, dict[str, Any]] = {
    "description": {"attribute_code": "description", "materialize_on_row_entity": True},
    "quantity": {"attribute_code": "quantity", "materialize_on_row_entity": True},
    "unit": {"attribute_code": "unit", "materialize_on_row_entity": True},
    "scheduled_date": {"attribute_code": "scheduled_date", "materialize_on_row_entity": True},
    "unit_price": {"attribute_code": "unit_price", "materialize_on_row_entity": True},
    "line_total": {"attribute_code": "line_total", "materialize_on_row_entity": True},
    "base_amount": {"attribute_code": "base_amount", "materialize_on_row_entity": True},
    "adjustment_amount": {"attribute_code": "adjustment_amount", "materialize_on_row_entity": True},
    "gross_amount": {"attribute_code": "gross_amount", "materialize_on_row_entity": True},
    "building_total_cost": {"attribute_code": "building_total_cost", "materialize_on_row_entity": True},
    "building_total_heating_cost": {"attribute_code": "building_total_heating_cost", "materialize_on_row_entity": True},
    "building_total_warmwater_cost": {"attribute_code": "building_total_warmwater_cost", "materialize_on_row_entity": True},
    "tenant_share_cost": {"attribute_code": "tenant_share_cost", "materialize_on_row_entity": True},
    "tenant_share_heating_cost": {"attribute_code": "tenant_share_heating_cost", "materialize_on_row_entity": True},
    "tenant_share_warmwater_cost": {"attribute_code": "tenant_share_warmwater_cost", "materialize_on_row_entity": True},
    "building_total_usage": {"attribute_code": "building_total_usage", "materialize_on_row_entity": True},
    "tenant_share_usage": {"attribute_code": "tenant_share_usage", "materialize_on_row_entity": True},
    "average_building_usage": {"attribute_code": "average_building_usage", "materialize_on_row_entity": True},
    "average_tenant_usage": {"attribute_code": "average_tenant_usage", "materialize_on_row_entity": True},
    "usage_unit": {"attribute_code": "usage_unit", "materialize_on_row_entity": True},
    "average_usage_unit": {"attribute_code": "average_usage_unit", "materialize_on_row_entity": True},
    "percentage_share": {"attribute_code": "percentage_share", "materialize_on_row_entity": True},
    "account_delta": {"attribute_code": "account_delta", "materialize_on_row_entity": True},
    "amount_due": {"attribute_code": "amount_due", "materialize_on_row_entity": True},
    "amount_paid": {"attribute_code": "amount_paid", "materialize_on_row_entity": True},
    "balance": {"attribute_code": "balance", "materialize_on_row_entity": True},
    "net_amount": {"attribute_code": "net_amount", "materialize_on_row_entity": True},
    "tax_amount": {"attribute_code": "tax_amount", "materialize_on_row_entity": True},
}


def default_field_binding(code: str) -> dict[str, Any]:
    return _FIELD_BINDINGS.get(code, {"entity_type": "document_fact", "attribute_code": code or "other"})


def default_row_binding(code: str) -> dict[str, Any]:
    return _ROW_BINDINGS.get(code, {"entity_type": "document_fact", "role_type": code or "other", "materialize_each_row": False})


def default_cell_binding(code: str) -> dict[str, Any]:
    return _CELL_BINDINGS.get(code, {"attribute_code": code or "other", "materialize_on_row_entity": True})
