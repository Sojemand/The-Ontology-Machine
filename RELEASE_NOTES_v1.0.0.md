# The Ontology Machine v1.0.0

This is the first public release candidate of The Ontology Machine.

It is a local-first Windows system for building evidence-bound semantic corpus
databases and working with them through Query, Ontology and Taxonomy Agents.

## Download

Download the all-in-one Windows installer from the release assets:

```text
OntologyMachine-AllInOne-Setup-2026-06-15.exe
```

Installer checksum:

```text
SHA256  1B4E7A88AF7333AAB6A7BB5CA9C08B34ADF6B288DDB85F92A4CF593D6C416706
```

## What Is Included

- All-in-one Windows installer.
- Client Frontend with Query Agent, Ontology Agent and Taxonomy Agent.
- Orchestrator and the document ingestion pipeline.
- Optimizer, Interpreter, Validator, Normalizer and Corpus Builder modules.
- Semantic Control Kernel and MCP Server.
- Edit Suite.
- Default demo database.
- Extractor tools for articles, YouTube subtitles and local audio/video
  transcription.
- Quickstart PDF and modular technical documentation.

## Default Demo

The installer includes the default demo corpus:

```text
SampleDB\Consciousness Travel - Default Demo\Corpus\corpus.db
```

The demo is the best first test target. It contains a prepared corpus and a
deep ontology layer suitable for trying the Query and Ontology Agents.

## Main Capabilities

- Build Artifact Trees from source files.
- Materialize page-grounded Corpus DBs.
- Preserve evidence through page images, raw extracts, structured outputs,
  normalized content, evidence atoms and DB backlinks.
- Run semantic search and source-grounded SQL/document inspection.
- Create and compare ontology lenses.
- Run Kernel-governed database creation, ingestion, merge, rebuild and reset
  workflows.
- Use optional extractor tools to prepare external material as Markdown input.

## Important Cost Notice

The Ontology Agent is token-intensive. This is not a bug.

For broad ontology work, expect many background model calls and tool calls. A
single serious turn can consume a large amount of input and output tokens. Keep
ontology mining focused and prefer small, highly correlated corpora.

Practical V1 recommendation:

```text
100 to 200 pages: good target range for serious ontology work
300 to 500 pages: possible, but cost and coverage become painful
1000+ pages: useful for Query Agent demos, not for broad Ontology Agent mining
```

## Known Boundaries

- Windows is the intended platform.
- Excel/CSV are not full V1 ingestion routes.
- Provider compatibility varies. Vision tasks need a vision-capable model.
- Some free or third-party models may fail tool-use or structured-output calls.
- Error Cases and review flags are expected evidence artifacts.
- Large sample DBs, if distributed separately, are query demos more than
  ontology-mining demos.
