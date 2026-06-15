from __future__ import annotations

from semantic_control_kernel.types.base import make_contract_types


_CONTRACT_TYPES = (
    ("CreateTaxonomyUpdateStateInput", "kernel.create_taxonomy_update_state.input.v1"),
    ("CreateProjectionsUpdateStateInput", "kernel.create_projections_update_state.input.v1"),
)

globals().update(make_contract_types(_CONTRACT_TYPES, __name__))

__all__ = [name for name, _schema_version in _CONTRACT_TYPES]
