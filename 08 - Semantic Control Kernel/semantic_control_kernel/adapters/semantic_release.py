from __future__ import annotations

from semantic_control_kernel.adapters.base import BasePipelineAdapter
from semantic_control_kernel.adapters.semantic_release_candidate_ops import SemanticReleaseCandidateMixin
from semantic_control_kernel.adapters.semantic_release_component_ops import SemanticReleaseComponentMixin
from semantic_control_kernel.adapters.semantic_release_publish_ops import SemanticReleasePublishMixin
from semantic_control_kernel.adapters.semantic_release_refs import (
    _artifact_root_from_semantic_release_folder,
    _included_taxonomy_codes,
    _projection_refs_from_identity,
    _projection_refs_from_payload,
    _projection_refs_from_update_state,
    _requires_detached_custom_release_write,
    _taxonomy_ref_from_payload,
)
from semantic_control_kernel.adapters.semantic_release_update_ops import SemanticReleaseUpdateMixin


class SemanticReleaseAdapter(
    SemanticReleasePublishMixin,
    SemanticReleaseComponentMixin,
    SemanticReleaseUpdateMixin,
    SemanticReleaseCandidateMixin,
    BasePipelineAdapter,
):
    adapter_name = "SemanticReleaseAdapter"


__all__ = [
    "SemanticReleaseAdapter",
    "_artifact_root_from_semantic_release_folder",
    "_included_taxonomy_codes",
    "_projection_refs_from_identity",
    "_projection_refs_from_payload",
    "_projection_refs_from_update_state",
    "_requires_detached_custom_release_write",
    "_taxonomy_ref_from_payload",
]
