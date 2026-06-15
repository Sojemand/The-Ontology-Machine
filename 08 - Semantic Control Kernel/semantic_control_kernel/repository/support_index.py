from __future__ import annotations

from semantic_control_kernel.repository.atomic_json import AtomicJsonStore
from semantic_control_kernel.repository.errors import ResumeStateNotFoundError
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.records import SupportBundleIndexRecord
from semantic_control_kernel.types.identity import SupportBundleRef


def _validate_support_index(payload: object) -> None:
    if not isinstance(payload, dict):
        raise TypeError("Support bundle index must be an object.")
    SupportBundleIndexRecord.from_dict(payload)


class SupportBundleIndex:
    def __init__(self, paths: StatePaths) -> None:
        self.paths = paths
        self._json = AtomicJsonStore(paths, "support")

    def append_support_bundle_ref(self, support_bundle_ref) -> None:
        ref_payload = support_bundle_ref.to_dict() if isinstance(support_bundle_ref, SupportBundleRef) else dict(support_bundle_ref)
        index = self._read_index()
        refs = [ref for ref in index.support_bundle_refs if ref.get("support_bundle_id") != ref_payload.get("support_bundle_id")]
        refs.append(ref_payload)
        payload = {
            "schema_version": SupportBundleIndexRecord.SCHEMA_VERSION,
            "support_bundle_refs": refs,
            "updated_at": utc_iso(),
        }
        self._json.write_json(self.paths.support_index_path, SupportBundleIndexRecord(payload).to_dict(), validator=_validate_support_index)

    def get_support_bundle_ref(self, support_bundle_id) -> SupportBundleRef:
        for ref in self._read_index().support_bundle_refs:
            if ref.get("support_bundle_id") == support_bundle_id:
                return SupportBundleRef.from_dict(ref)
        raise ResumeStateNotFoundError(f"Support bundle ref not found: {support_bundle_id}")

    def list_support_bundle_refs(self, workflow_run_id=None) -> list[SupportBundleRef]:
        refs = []
        for ref in self._read_index().support_bundle_refs:
            if workflow_run_id is None or ref.get("workflow_run_id") == workflow_run_id:
                refs.append(SupportBundleRef.from_dict(ref))
        return refs

    def _read_index(self) -> SupportBundleIndexRecord:
        return SupportBundleIndexRecord.from_dict(self._json.read_json(self.paths.support_index_path, validator=_validate_support_index))
