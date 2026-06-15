from __future__ import annotations

from dataclasses import dataclass

from semantic_control_kernel.types.debug import REDACTION_PROFILE_IDS


class RedactionProfile:
    SUPPORT_SAFE_V1 = REDACTION_PROFILE_IDS[0]
    USER_VISIBLE_V1 = REDACTION_PROFILE_IDS[1]
    INTERNAL_REF_ONLY_V1 = REDACTION_PROFILE_IDS[2]


@dataclass
class RedactionStats:
    redacted_field_counts: dict[str, int]
    redacted_path_counts: dict[str, int]
    redacted_secret_counts: dict[str, int]
    raw_payload_refs_excluded: list[str]

    @classmethod
    def empty(cls) -> "RedactionStats":
        return cls(redacted_field_counts={}, redacted_path_counts={}, redacted_secret_counts={}, raw_payload_refs_excluded=[])

    def bump_field(self, field_name: str) -> None:
        self.redacted_field_counts[field_name] = self.redacted_field_counts.get(field_name, 0) + 1

    def bump_path(self, path_kind: str) -> None:
        self.redacted_path_counts[path_kind] = self.redacted_path_counts.get(path_kind, 0) + 1

    def bump_secret(self, secret_kind: str) -> None:
        self.redacted_secret_counts[secret_kind] = self.redacted_secret_counts.get(secret_kind, 0) + 1

    def exclude_raw_ref(self, ref_name: str) -> None:
        if ref_name not in self.raw_payload_refs_excluded:
            self.raw_payload_refs_excluded.append(ref_name)
