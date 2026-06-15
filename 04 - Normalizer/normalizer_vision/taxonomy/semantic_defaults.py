"""Semantic defaults for taxonomy upgrade."""
from __future__ import annotations

from typing import Any

DEFAULT_MASTER_COMPATIBILITY: dict[str, Any] = {
    "taxonomy_contract": "semantic_release_v1",
    "backward_compatible_with": ["1.0"],
    "notes": [
        "v1 Master-Taxonomien werden additiv zu semantic_release_v1 erweitert.",
        "Projection-Dateien bleiben include-list-kompatibel und koennen schrittweise Semantikmetadaten erhalten.",
    ],
}

DEFAULT_ENTITY_TYPES = [
    {"code": "party", "label": "Party", "description": "Person or organization in the document context."},
    {"code": "address", "label": "Address", "description": "Adresse oder ortsbezogene Anschrift."},
    {"code": "identifier", "label": "Identifier", "description": "Document, case or reference identifier."},
    {"code": "financial_amount", "label": "Financial Amount", "description": "Monetaerer oder saldobezogener Wert."},
    {"code": "period", "label": "Period", "description": "Zeitspanne, Frist oder Zeitraum."},
    {"code": "property", "label": "Property", "description": "Objekt-, Liegenschafts- oder Bestandskontext."},
    {"code": "document_fact", "label": "Document Fact", "description": "Document-level semantic fact."},
    {"code": "line_item", "label": "Line Item", "description": "Positions- oder Zeilenentitaet."},
    {"code": "measurement", "label": "Measurement", "description": "Mess- oder Verbrauchszeile."},
    {"code": "event", "label": "Event", "description": "Vorgang, Ablauf oder relationale Zeile."},
]

DEFAULT_ROLE_TYPES = [
    {"code": "issuer", "label": "Issuer"},
    {"code": "sender", "label": "Sender"},
    {"code": "recipient", "label": "Recipient"},
    {"code": "recipient_primary", "label": "Recipient Primary"},
    {"code": "customer", "label": "Customer"},
    {"code": "tenant", "label": "Tenant"},
    {"code": "owner", "label": "Owner"},
    {"code": "property_manager", "label": "Property Manager"},
    {"code": "property_address", "label": "Property Address"},
    {"code": "contact_person", "label": "Contact Person"},
    {"code": "carrier", "label": "Carrier"},
    {"code": "loading", "label": "Loading"},
    {"code": "transfer", "label": "Transfer"},
    {"code": "unloading", "label": "Unloading"},
    {"code": "our_reference", "label": "Our Reference"},
    {"code": "your_reference", "label": "Your Reference"},
    {"code": "vehicle_registration", "label": "Vehicle Registration"},
    {"code": "schedule_entry", "label": "Schedule Entry"},
    {"code": "account_entry", "label": "Account Entry"},
    {"code": "measurement_entry", "label": "Measurement Entry"},
    {"code": "timeline_entry", "label": "Timeline Entry"},
]

DEFAULT_RELATION_TYPES = [
    {"code": "normalized_from", "label": "Normalized From"},
    {"code": "document_has_entity", "label": "Document Has Entity"},
    {"code": "entity_reference", "label": "Entity Reference"},
]
