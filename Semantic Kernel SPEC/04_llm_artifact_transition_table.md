# LLM Artifact Transition Table

Current isolated LLM functions are creation/readout support only. They do not mutate an existing database or derive update candidates for a filled database.

| LLM function | Input contract | Output contract | Run folder |
| --- | --- | --- | --- |
| `analyze_samples` | `array[kernel.analyze_sample.input.v1]` | `kernel.sample_analyses.v1` | `sample_analysis_requests/<analysis_run_id>/` |
| `user_report_samples` | `kernel.sample_analyses.v1.user_report_samples_seed` | `plain_markdown.user_report_samples.v1` | `sample_analysis_requests/<analysis_run_id>/` |
| `create_taxonomy_to_sample_analyses` | `kernel.create_taxonomy_to_sample_analyses.input.v1` | `kernel.taxonomy_to_sample_analyses.v1` | `taxonomy_to_sample_analysis_requests/<analysis_run_id>/` |
| `create_projections_to_sample_analyses` | `kernel.create_projections_to_sample_analyses.input.v1` | `kernel.projections_to_sample_analyses.v1` | `projection_to_sample_analysis_requests/<analysis_run_id>/` |

## Artifact Rules

- All LLM calls write `prompt_snapshot.json` and `llm_response.raw.json` in the function run folder.
- Database-creation routes that author custom taxonomy or projection artifacts set the LLM artifact root to `<artifact_root>/Semantic Release`.
- Only `create_taxonomy_to_sample_analyses` and `create_projections_to_sample_analyses` feed update-state builders, and those builders create creation precursor states only.
- Existing-database modification, database-coverage analysis and comparison-based update flows are retired and are not live Kernel contracts.
