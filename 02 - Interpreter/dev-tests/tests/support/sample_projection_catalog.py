from __future__ import annotations


def build_sample_projection_catalog() -> dict:
    return {
        "catalog_version": "catalog.2026-03-28",
        "master_taxonomy_version": "2026-03-28.v5",
        "projections": [
            {
                "projection_id": "community.spiritual.default.v1",
                "label": "Community Spiritual Default v1",
                "when_to_use": "Membership, community events, donations, pastoral care, and spiritual guidance documents for groups, clubs, or congregations.",
                "avoid_when": "Avoid for technical engineering files, formal HR identity dossiers, medical prescriptions, or housing and property administration.",
                "example_document_types": ["membership_record", "statement", "schedule", "general_letter", "certificate"],
            },
            {
                "projection_id": "finance.default.v1",
                "label": "Finance Default v1",
                "when_to_use": "Invoices, statements, payroll, tax, reimbursement, customer or vendor account, and budget-planning documents.",
                "avoid_when": "Avoid for rent, utilities, tenant or property management, engineering specs, identity dossiers, and personal wellbeing or community care documents.",
                "example_document_types": ["invoice", "statement", "payslip", "quote", "policy"],
            },
            {
                "projection_id": "health.care.default.v1",
                "label": "Health Care Default v1",
                "when_to_use": "Medical administration, treatment plans, prescriptions, health insurance, care-level, and medical certificate documents.",
                "avoid_when": "Avoid for generic HR identity records, finance-only reimbursements, technical maintenance logs, or community membership and event documents.",
                "example_document_types": ["prescription", "certificate", "statement", "schedule", "form"],
            },
            {
                "projection_id": "housing.default.v1",
                "label": "Housing Default v1",
                "when_to_use": "Housing, utilities, rent, payments, property management, tenant communication.",
                "avoid_when": "Avoid for logistics, procurement, technical execution plans, or personal recovery plans.",
                "example_document_types": ["invoice", "advance_payment", "utility_cost_statement", "contract", "general_letter"],
            },
            {
                "projection_id": "legal.public_admin.default.v1",
                "label": "Legal Public Admin Default v1",
                "when_to_use": "Contracts, authority notices, permits, registrations, compliance notices, civic-service, and benefit-case documents.",
                "avoid_when": "Avoid for housing utility statements, logistics execution records, generic payroll, or personal wellbeing journals.",
                "example_document_types": ["contract", "authority_notice", "application", "certificate", "form"],
            },
            {
                "projection_id": "operations.default.v1",
                "label": "Operations Default v1",
                "when_to_use": "Logistics, procurement, technical specification, execution plan, site access, inventory.",
                "avoid_when": "Avoid for rent, utility-cost, tenant-administration, or housing finance documents.",
                "example_document_types": ["delivery_note", "order", "specification", "report", "form"],
            },
            {
                "projection_id": "people.identity.default.v1",
                "label": "People Identity Default v1",
                "when_to_use": "Identity proofs, profiles, HR and employment records, education records, personnel requests, and person-centric certificates.",
                "avoid_when": "Avoid for finance-led invoices or statements, technical asset files, medical treatment plans, or community worship and event material.",
                "example_document_types": ["profile", "payslip", "certificate", "application", "form"],
            },
            {
                "projection_id": "personal.wellbeing.default.v1",
                "label": "Personal Wellbeing Default v1",
                "when_to_use": "Personal wellbeing plans, self-reflection, habit tracking, coaching, and recovery-oriented support documents.",
                "avoid_when": "Avoid for formal medical administration, payroll or finance, legal notices, or community membership ledgers.",
                "example_document_types": ["schedule", "profile", "policy", "report", "form"],
            },
            {
                "projection_id": "technical.default.v1",
                "label": "Technical Default v1",
                "when_to_use": "Technical specs, inspections, maintenance, asset or site documentation, engineering changes, QA, and equipment records.",
                "avoid_when": "Avoid for rent or tenant administration, finance-only statements, formal identity dossiers, or pastoral and wellbeing documents.",
                "example_document_types": ["specification", "inspection_report", "meter_reading", "report", "form"],
            },
        ],
    }
