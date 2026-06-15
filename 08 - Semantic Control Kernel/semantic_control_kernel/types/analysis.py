from __future__ import annotations

from semantic_control_kernel.types.base import make_contract_types


_CONTRACT_TYPES = (
    ("AnalyzeSampleInput", "kernel.analyze_sample.input.v1"),
    ("SampleAnalyses", "kernel.sample_analyses.v1"),
    ("TaxonomyProjectionAuthoringView", "kernel.taxonomy_projection_authoring_view.v1"),
    ("CreateTaxonomyToSampleAnalysesInput", "kernel.create_taxonomy_to_sample_analyses.input.v1"),
    ("CreateProjectionsToSampleAnalysesInput", "kernel.create_projections_to_sample_analyses.input.v1"),
    ("TaxonomyToSampleAnalyses", "kernel.taxonomy_to_sample_analyses.v1"),
    ("ProjectionsToSampleAnalyses", "kernel.projections_to_sample_analyses.v1"),
)

globals().update(make_contract_types(_CONTRACT_TYPES, __name__))

__all__ = tuple(name for name, _schema_version in _CONTRACT_TYPES)
