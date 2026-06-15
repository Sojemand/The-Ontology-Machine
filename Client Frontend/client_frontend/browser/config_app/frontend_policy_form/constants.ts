export const SOURCE_ORDER_VALUES = ["live", "cache", "seed", "fallback"] as const;

export const PROMPT_FIELD_ORDER = [
  ["identity", "Identity"],
  ["analysis", "Analysis"],
  ["evidence", "Evidence"],
  ["data_layers", "Data Layers"],
  ["tool_routing", "Tool-Routing"],
  ["workbench", "Workbench"],
  ["answer_rules", "Answer Rules"]
] as const;

export const ONTOLOGY_PROMPT_FIELD_ORDER = [
  ["identity", "Identity"],
  ["mission", "Mission"],
  ["intent_architecture", "Intent Architecture"],
  ["analysis", "Analysis"],
  ["working_method", "Working Method"],
  ["data_layers", "Data Layers"],
  ["ontology_layers", "Ontology Layers"],
  ["tool_routing", "Tool-Routing"],
  ["lens_lifecycle", "Lens Lifecycle"],
  ["foreign_key_order", "Foreign-Key Order"],
  ["insert_contract", "Insert Contract"],
  ["write_discipline", "Write Discipline"],
  ["preflight_repair", "Preflight Repair"],
  ["write_policy", "Write Policy"],
  ["evidence_policy", "Evidence Policy"],
  ["answer_rules", "Answer Rules"]
] as const;

export const SOURCE_ORDER_LABELS = ["1. Priority", "2. Priority", "3. Priority", "4. Priority"] as const;
