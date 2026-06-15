# The Machine Doku

This folder is the modular documentation set for The Ontology Machine.

It has two jobs:

1. Give a new user a clean first path into the system.
2. Give a technical reader enough structure to understand ownership, artifacts,
   workflows, databases, agents, configuration and production boundaries.

The docs are intentionally split into chapters. The Machine itself is modular,
so the documentation should be modular too. A reader should not have to swallow
one huge manual before finding the one thing they need.

## Start Here

Read this first:

1. [Quickstart](Quickstart_Handbook)

The Quickstart is the front door. It explains the basic mental model, the demo
DB, the Frontend, the Orchestrator, the three agents, the Artifact Tree, the
Corpus DB and the first troubleshooting steps.

Then read:

2. [The Design](00_The_Design.md)

The Design chapter explains why the system exists in this shape. It is less a
button manual and more the rationale behind the architecture.

After that, use the technical chapters as needed.

## Documentation Map

| Chapter | Purpose |
| --- | --- |
| [Quickstart](Quickstart_Handbook) | First entry path for users who want to open the system and understand the basics. |
| [The Design](00_The_Design.md) | Design rationale, history, tradeoffs and product idea. |
| [System Overview](01_System_Overview.md) | Clean high-level map of what the Machine is and how data flows through it. |
| [Architecture Map](02_Architecture_Map.md) | Ownership boundaries, module relationships and runtime topology. |
| [Module Catalog](03_Module_Catalog.md) | What each module owns, where it lives and how it connects to the others. |
| [Contract Library](04_Contract_Library.md) | Cross-module contracts, schemas, owner interfaces and handoff shapes. |
| [Workflow Catalog](05_Workflow_Catalog.md) | Kernel and pipeline workflows, routes, states and recovery paths. |
| [Artifact Tree Guide](06_Artifact_Tree_Guide.md) | Folder structure around a corpus and why each artifact exists. |
| [Database Documentation](07_Database_Documentation.md) | Corpus DB layers, schema concepts, Base Graph, ontology tables and inspection paths. |
| [Agent Documentation](08_Agent_Documentation.md) | Query Agent, Ontology Agent, Taxonomy Agent and their tool boundaries. |
| [Configuration & Credentials](09_Configuration_Credentials.md) | Provider credentials, model settings, config surfaces and local state. |
| [Operator Guides](10_Operator_Guides.md) | Practical operating procedures, recovery steps and runbook material. |
| [Testing & Verification](11_Testing_Verification.md) | How to verify modules, workflows, DBs, installers and release candidates. |
| [Production Handover Notes](12_Production_Handover_Notes.md) | Honest boundary between V1 reference implementation and field-hardened product. |

## Recommended Reading Paths

### First-Time User

1. [Quickstart](Quickstart_Handbook)
2. [System Overview](01_System_Overview.md)
3. [Artifact Tree Guide](06_Artifact_Tree_Guide.md)
4. [Agent Documentation](08_Agent_Documentation.md)
5. [Configuration & Credentials](09_Configuration_Credentials.md)

### Operator

1. [Quickstart](Quickstart_Handbook)
2. [Operator Guides](10_Operator_Guides.md)
3. [Configuration & Credentials](09_Configuration_Credentials.md)
4. [Artifact Tree Guide](06_Artifact_Tree_Guide.md)
5. [Database Documentation](07_Database_Documentation.md)

### Developer

1. [System Overview](01_System_Overview.md)
2. [Architecture Map](02_Architecture_Map.md)
3. [Module Catalog](03_Module_Catalog.md)
4. [Contract Library](04_Contract_Library.md)
5. [Workflow Catalog](05_Workflow_Catalog.md)
6. [Testing & Verification](11_Testing_Verification.md)

### Debugger / Maintainer

1. [Architecture Map](02_Architecture_Map.md)
2. [Artifact Tree Guide](06_Artifact_Tree_Guide.md)
3. [Database Documentation](07_Database_Documentation.md)
4. [Workflow Catalog](05_Workflow_Catalog.md)
5. [Operator Guides](10_Operator_Guides.md)
6. [Production Handover Notes](12_Production_Handover_Notes.md)

### Handover Engineer

1. [The Design](00_The_Design.md)
2. [System Overview](01_System_Overview.md)
3. [Architecture Map](02_Architecture_Map.md)
4. [Module Catalog](03_Module_Catalog.md)
5. [Contract Library](04_Contract_Library.md)
6. [Testing & Verification](11_Testing_Verification.md)
7. [Production Handover Notes](12_Production_Handover_Notes.md)

## The Short Mental Model

The Machine has four things a reader should never confuse:

```text
Artifact Tree  = evidence and rebuild surface
Corpus DB      = queryable materialized corpus
Frontend       = user-facing agent and source viewer surface
Orchestrator   = direct ingestion pipeline control surface
```

The rest of the documentation expands that model.

The Optimizer, Interpreter, Validator, Normalizer and Corpus Builder form the
document pipeline. The Semantic Control Kernel governs long workflows. The MCP
Server exposes those workflows as tools. The Client Frontend presents the
Query, Ontology and Taxonomy Agents. The Artifact Tree and Corpus DB keep the
evidence trail open to inspection.

If a reader understands that, the system stops looking like a pile of modules
and starts looking like what it is: a local machine for turning documents into
evidence-bound, queryable, versioned semantic matter.

## Documentation Principles

### Keep Ownership Visible

Every chapter should make clear which module owns which truth. If something
fails, the first useful question is not "where can I patch this?" but "which
owner owns this state?"

### Keep Evidence Visible

The Machine is evidence-first. Documentation should point to the files, folders,
tables, requests, outputs, logs or UI surfaces that prove a claim.

### Keep Runtime State Separate From Durable Truth

Do not mix up:

- source artifacts
- generated artifacts
- Corpus DB state
- Semantic Release state
- Kernel workflow state
- Frontend session state
- credentials
- logs and temporary runtime files

Many real bugs come from treating those as if they were the same kind of thing.

### Keep The Quickstart Short

The Quickstart should stay readable. Deep SQL, long recovery details and module
contracts belong in the later chapters.

## Suggested Merge Order

If these chapters are merged into one handbook, use this order:

1. [Quickstart](Quickstart_Handbook)
2. [The Design](00_The_Design.md)
3. [System Overview](01_System_Overview.md)
4. [Architecture Map](02_Architecture_Map.md)
5. [Artifact Tree Guide](06_Artifact_Tree_Guide.md)
6. [Database Documentation](07_Database_Documentation.md)
7. [Agent Documentation](08_Agent_Documentation.md)
8. [Configuration & Credentials](09_Configuration_Credentials.md)
9. [Operator Guides](10_Operator_Guides.md)
10. [Workflow Catalog](05_Workflow_Catalog.md)
11. [Module Catalog](03_Module_Catalog.md)
12. [Contract Library](04_Contract_Library.md)
13. [Testing & Verification](11_Testing_Verification.md)
14. [Production Handover Notes](12_Production_Handover_Notes.md)

This order starts with the user-facing path, then explains the idea, then walks
down into architecture, evidence, database, agents, operations and finally
handover boundaries.
