from __future__ import annotations

from normalizer_vision.taxonomy.promotion_rules import promotion_rules_from_fields


def test_explicit_promotion_rules_drop_empty_source_path_placeholders() -> None:
    fields = [
        {"code": "issuer", "promotion_slot": "counterparty"},
        {"code": "amount_due", "promotion_slot": "amount_due"},
    ]

    rules = promotion_rules_from_fields(
        fields,
        include_field_codes=["issuer", "amount_due"],
        explicit_rules=[
            {"slot": "counterparty", "source_paths": ["content.fields.issuer"]},
            {"slot": "amount_due", "source_paths": []},
        ],
    )

    assert rules == [{"slot": "counterparty", "source_paths": ["content.fields.issuer"]}]
