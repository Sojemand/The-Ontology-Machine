# LLM User Reports

> Split from SPEC_Semantic_Runtime_Kernel_New.md.
> Source path: C:\Users\Norma\Workspace\The Ontology Machine\SPEC_Semantic_Runtime_Kernel_New.md.
> Source lines: 3096-3242.

user_report_samples and user_report_database prompts and standardized markdown report structures.

---

user_report_samples
	- The Kernel injects `user_report_samples_seed` from `kernel.sample_analyses.v1` into one isolated LLM call.
	- The LLM creates a standardized user-facing report as plain text.
	- The report explains what the sample set shows from taxonomy and projection perspective.
	- The report is informational only. It does not create, modify, validate or activate taxonomy or projections.
	- The generated report is written into the Artifact Tree so it remains available for review and later comparison:
		- `sample_analysis_requests/<analysis_run_id>/user_report_samples.md`

	- Prompt structure:
		```text
		You are writing a clear user-facing sample analysis report. Use the same language as the user.

		You receive `user_report_samples_seed` from a prior semantic sample-set analysis. The seed contains findings about what the sample documents show together, how their content maps to taxonomy concepts, and how that content could be covered by one or more projections.

		Write a plain-language report for the user. The user should understand what was found and why it matters.

		Do not output JSON. Do not mention internal function names, schema versions, downstream consumers, pipeline mechanics or implementation details.

		This report is informational only. It must not claim that any taxonomy or projection will be created, changed, validated or activated. It must not describe pipeline next steps. Later Kernel actions may use separate analysis calls and may not exactly match this report.

		Use exactly the report structure below. Keep the headings exactly as written.

		# Sample Analysis Report

		## 1. Overview
		Explain what kind of sample set was analyzed and what it appears to represent.

		## 2. What The Samples Show
		Explain the common semantic pattern across the samples. Describe the shared document family, recurring content, and meaningful variations.

		## 3. Taxonomy Perspective
		Explain which domains, document types, categories, subcategories, fields, rows or cells appear relevant. Use plain language and avoid code-heavy wording unless a code is important for user confirmation.

		## 4. Projection Perspective
		Explain what projection boundary appears appropriate. State whether one projection seems sufficient or whether a split may be useful. Explain why this matters for covering the sample content.

		## 5. Important Findings
		List the most important findings as short bullets. Focus on what the user should understand about the sample set.

		## 6. Points To Review
		List uncertainties, naming questions, boundary questions or semantic ambiguities visible in the analysis. Do not describe pipeline steps or tell the user what the system will do next.

		Writing rules:
		- Be comprehensive, not terse.
		- Use clear non-technical language.
		- Do not invent findings not present in the seed.
		- Do not propose final validated taxonomy or projection changes.
		- Avoid implementation vocabulary.
		- Keep the report standardized and easy to compare with other sample reports.

		Input:
		{{user_report_samples_seed_json}}
		```

	- Output structure:
		- Plain text report.
		- Must use exactly these headings:
			- `# Sample Analysis Report`
			- `## 1. Overview`
			- `## 2. What The Samples Show`
			- `## 3. Taxonomy Perspective`
			- `## 4. Projection Perspective`
			- `## 5. Important Findings`
			- `## 6. Points To Review`
		- No JSON.
		- No metadata block.
		- No schema version.
		- No pipeline next steps.

user_report_database
	- Database-level report generation from Kernel LLM analysis is retired; only sample-report generation remains live.
	- The LLM creates a standardized user-facing database coverage report as plain text.
	- The report explains how well the active taxonomy and projections represent the processed database.
	- The report is informational only. It does not create, modify, validate or activate taxonomy or projections.
	- The generated report is written into the Artifact Tree so it remains available for review and later comparison:
		- `database_analysis_requests/<analysis_run_id>/user_report_database.md`

	- Prompt structure:
		```text
		You are writing a clear user-facing database coverage report. Use the same language as the user.

		You receive `user_report_database_seed` from a prior database coverage analysis. The seed contains findings about how well the processed database is represented by the active taxonomy and projections, whether records were materialized under one or several semantic release versions, where `other` or review signals appear, where useful values are not projection-backed, and which additive coverage opportunities may exist.

		Write a plain-language report for the user. The user should understand how well their database content is represented, where coverage is strong, where coverage is weak, and which points may need review.

		Do not output JSON. Do not mention internal function names, schema versions, downstream consumers, SQL queries, table names, pipeline mechanics or implementation details.

		This report is informational only. It must not claim that any taxonomy or projection will be created, changed, validated or activated. It must not describe pipeline next steps. Later Kernel actions may use separate analysis calls and may not exactly match this report.

		Use exactly the report structure below. Keep the headings exactly as written.

		# Database Coverage Report

		## 1. Overview
		Explain what database coverage was analyzed and give a clear high-level assessment of how well the active semantic setup represents the database content. If the seed says records come from different release versions, explain that distinction in plain language.

		## 2. Overall Coverage Quality
		Explain the main coverage strengths and weaknesses. Include important counts or ratios only when they help the user understand the situation.

		## 3. Taxonomy Coverage
		Explain how well document types, categories, subcategories, fields, rows and cells are represented. Describe missing or under-covered semantics in plain language.

		## 4. Projection Coverage
		Explain how well the active projections cover the documents assigned to them. Describe where a projection appears too narrow, too generic or only partially fitting.

		## 5. Other And Review Signals
		Explain where `other` classifications, generic fields, review flags or uncertainty signals appear, and what they mean for the user.

		## 6. Unbacked Values
		Explain useful values that appear in the database but are not clearly backed by projection promotion rules or semantic coverage.

		## 7. Additive Coverage Opportunities
		Describe possible additive coverage improvements in plain language. Present them as opportunities visible in the report, not as actions the system will take.

		## 8. Points To Review
		List uncertainties, naming questions, boundary questions or semantic ambiguities visible in the analysis. Do not describe pipeline steps or tell the user what the system will do next.

		Writing rules:
		- Be comprehensive, not terse.
		- Use clear non-technical language.
		- Do not invent findings not present in the seed.
		- Do not propose final validated taxonomy or projection changes.
		- Avoid implementation vocabulary.
		- Explain `other` as content that could not be represented more specifically.
		- Keep the report standardized and easy to compare with other database reports.

		Input:
		{{user_report_database_seed_json}}
		```

	- Output structure:
		- Plain text report.
		- Must use exactly these headings:
			- `# Database Coverage Report`
			- `## 1. Overview`
			- `## 2. Overall Coverage Quality`
			- `## 3. Taxonomy Coverage`
			- `## 4. Projection Coverage`
			- `## 5. Other And Review Signals`
			- `## 6. Unbacked Values`
			- `## 7. Additive Coverage Opportunities`
			- `## 8. Points To Review`
		- No JSON.
		- No metadata block.
		- No schema version.
		- No pipeline next steps.
