export type ChatAgentType = "query" | "pipeline" | "ontology";

export function routeForAgent(agent: ChatAgentType | undefined, routes: { query: string; pipeline: string; ontology: string }): string {
  if (agent === "pipeline") return routes.pipeline;
  if (agent === "ontology") return routes.ontology;
  return routes.query;
}
