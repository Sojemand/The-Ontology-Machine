from __future__ import annotations


CONSTANT_FIELD_RULES: dict[str, dict[str, str]] = {
    "kernel.sample_analyses.v1": {
        "analysis_scope": "sample_set",
        "input_contract": "kernel.analyze_sample.input.v1",
    },
    "kernel.taxonomy_to_sample_analyses.v1": {
        "source_schema_version": "kernel.sample_analyses.v1",
        "analysis_scope": "sample_set",
    },
    "kernel.projections_to_sample_analyses.v1": {
        "source_schema_version": "kernel.sample_analyses.v1",
        "taxonomy_view_schema_version": "kernel.taxonomy_projection_authoring_view.v1",
        "analysis_scope": "sample_set",
    },
    "kernel.create_taxonomy_update_state.input.v1": {
        "source_schema_version": "kernel.taxonomy_to_sample_analyses.v1",
        "analysis_scope": "sample_set",
    },
    "kernel.create_projections_update_state.input.v1": {
        "source_schema_version": "kernel.projections_to_sample_analyses.v1",
        "taxonomy_view_schema_version": "kernel.taxonomy_projection_authoring_view.v1",
        "analysis_scope": "sample_set",
    },
}
