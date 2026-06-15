"""Alias and hint data for context promotion policy."""
from __future__ import annotations

ROW_LABEL_KEYS = ("position", "beschreibung", "description", "item", "label", "title", "text", "name", "posten", "leistung")
NET_KEYS = ("net_amount", "netto", "netto_eur", "betrag_netto", "net")
TAX_KEYS = ("tax_amount", "umsatzsteuer", "umsatzsteuer_eur", "mwst", "ust", "vat")
GROSS_KEYS = ("total_monetary_value", "gross_amount", "gross", "gross_eur", "brutto", "brutto_eur", "amount_due", "total", "betrag")
DUE_ROW_HINTS = ("zu zahlender", "zu zahlen", "zahlbetrag", "restbetrag", "offener betrag", "saldo", "faelliger betrag", "endbetrag")
TOTAL_ROW_HINTS = ("gesamt", "gesamtkosten", "summe", "subtotal", "zwischensumme", "gesamtbetrag")
BLOCKED_CONTEXT_KEYS = ("durchschnittlicher_stundensatz", "overtime_hours", "net_salary")
CURRENCY_ALIASES = ("currency", "currencies")
FIELD_ALIAS_MAP = {
    "company": ("company", "supplier", "vendor", "issuer", "sender", "organization", "organisation"),
    "document_date": ("invoice_date", "document_date", "date"),
    "document_title": ("document_title", "title", "invoice_type", "subject"),
    "description": ("description", "summary"),
    "reference_number": ("reference_number", "invoice_number", "document_number", "rechnungsnummer", "rechnungs_nr", "rechnungsnr", "belegnummer", "contract_number", "record_number", "file_number", "vertragsnummer"),
    "document_number": ("document_number", "invoice_number", "reference_number"),
    "invoice_number": ("invoice_number", "document_number", "reference_number"),
    "due_date": ("due_date", "payment_due_date", "debit_date", "faellig_am", "faellig", "faelligkeit", "zahlbar_bis"),
    "recipient_name": ("recipient_name", "customer_name", "customer", "recipient", "member_name", "tenant", "contract_partner", "empfaenger", "rechnungsempfaenger"),
    "customer_number": ("customer_number", "customer_no", "kundennummer", "mitgliedsnummer"),
    "total_hours": ("total_hours", "hours_total", "hours", "gesamtstunden"),
    "opening_balance": ("opening_balance", "start_balance"),
    "closing_balance": ("closing_balance", "end_balance", "balance", "closing_amount", "balance_amount"),
}
REFERENCE_ALIAS_MAP = FIELD_ALIAS_MAP | {
    "total_monetary_value": ("amount_due", "gross_amount", "total_monetary_value", "monetary_value", "total_amount", "brutto", "brutto_eur", "gross", "gross_eur", "betrag"),
    "net_amount": ("net_amount", "netto", "netto_eur", "betrag_netto", "net", "net_value", "subtotal_amount", "nettobetrag", "netto_verdienst", "gesamt_netto"),
    "tax_amount": ("tax_amount", "vat_amount", "mwst_betrag", "umsatzsteuer", "umsatzsteuer_eur", "mwst", "ust", "mwst_amount", "ust_amount"),
    "tax_rate": ("tax_rate", "vat_rate", "mwst_satz", "mwst_rate", "ust_rate"),
}
COUNTERPARTY_ALIASES = FIELD_ALIAS_MAP["recipient_name"] + ("counterparty",)
