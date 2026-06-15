export interface TaxonomyWorkflowOption {
  toolName: string;
  label: string;
  description: string;
}

export const TAXONOMY_WORKFLOW_OPTIONS: TaxonomyWorkflowOption[] = [
  {
    toolName: "empty_database_no_semantic_release",
    label: "Empty DB, no release",
    description: "Create an empty corpus target without attaching a Semantic Release."
  },
  {
    toolName: "empty_database_default_taxonomy_no_projections",
    label: "Default taxonomy, no projections",
    description: "Create a target with the default taxonomy only."
  },
  {
    toolName: "empty_database_default_taxonomy_default_projections",
    label: "Default taxonomy and projections",
    description: "Create a target with default taxonomy and default projections."
  },
  {
    toolName: "empty_database_default_taxonomy_custom_projections",
    label: "Default taxonomy, custom projections",
    description: "Create a target with default taxonomy and user-shaped projections."
  },
  {
    toolName: "empty_database_custom_taxonomy_no_projections",
    label: "Custom taxonomy, no projections",
    description: "Create a target with a custom taxonomy path and no projections."
  },
  {
    toolName: "empty_database_custom_taxonomy_custom_projections",
    label: "Custom taxonomy and projections",
    description: "Create a target with custom taxonomy and custom projections."
  },
  {
    toolName: "manual_pipeline_run",
    label: "Manual pipeline run",
    description: "Run the pipeline against the selected configured target."
  },
  {
    toolName: "database_merge_additive_only",
    label: "Merge database, additive",
    description: "Merge materialized data additively without destructive replacement."
  },
  {
    toolName: "database_rebuild_from_artifacts",
    label: "Rebuild from artifacts",
    description: "Rebuild the corpus database from the existing artifact tree."
  },
  {
    toolName: "create_custom_taxonomy_path",
    label: "Create custom taxonomy",
    description: "Start the Kernel path for authoring a custom taxonomy."
  },
  {
    toolName: "create_custom_projection_path",
    label: "Create custom projection",
    description: "Start the Kernel path for authoring custom projections."
  },
  {
    toolName: "reset_database",
    label: "Reset database",
    description: "Start the guarded Kernel database reset path."
  }
];

export function buildTaxonomyWorkflowCommand(toolName: string): string {
  const option = TAXONOMY_WORKFLOW_OPTIONS.find((candidate) => candidate.toolName === toolName);
  if (!option) return "";
  return `Run Taxonomy Agent workflow \`${option.toolName}\`. This was selected from the workflow menu; use the matching visible Kernel workflow tool.`;
}
