# The Ontology Machine

The Ontology Machine is a local-first Windows system for turning heterogeneous
documents into evidence-bound semantic corpus databases.

It ingests files, renders evidence artifacts, runs a staged LLM-assisted
pipeline, validates and normalizes the results through a Semantic Release,
materializes everything into a SQLite Corpus DB, and lets agents query, inspect
and mine that corpus through a local browser frontend.

The short version:

```text
Artifact Tree  = evidence and rebuild surface
Corpus DB      = queryable materialized corpus
Frontend       = user-facing agent and page viewer surface
Orchestrator   = direct ingestion and pipeline debugging surface
```

This is Version 1.0. It is working software, but it is also an honest reference
implementation of a large solo-built research tool. It is not a cloud service,
not a polished SaaS product, and not a guaranteed field-hardened enterprise
deployment.

## What It Does

- Builds local Artifact Trees around source files.
- Materializes source documents into SQLite Corpus databases.
- Preserves visible page evidence through page images and DB evidence links.
- Uses Semantic Releases as the active taxonomy/projection contract.
- Provides a Query Agent for source-grounded corpus questions.
- Provides an Ontology Agent for evidence-bound ontology lenses.
- Provides a Taxonomy Agent for Kernel-governed creation, merge, rebuild,
  reset and ingestion workflows.
- Supports optional extractor tools for articles, YouTube subtitles and local
  audio/video transcription.

## What It Is Good For

The strongest V1 use cases are small to medium specialized corpora:

- papers and review packets
- article collections
- books or chapters
- research folders
- media transcripts
- legal or administrative document sets
- evidence-heavy qualitative analysis

The Query Agent can work over larger databases. The Ontology Agent should be
used with restraint: broad ontology work is token-intensive and is best kept to
roughly 100 to 200 pages if cost matters.

## Download

The recommended user path is the GitHub Release installer, not cloning the
repo.

Download the latest release from:

```text
https://github.com/Sojemand/The-Ontology-Machine/releases/latest
```

The release assets include the Windows installer, checksum file, Quickstart PDF
and optional sample database archives.

## Quick Start

After installation, start with the Quickstart PDF placed next to the desktop
shortcuts, or read the source documentation here:

```text
The Machine Doku\Quickstart_Handbook
The Machine Doku\README.md
```

Normal launchers in a source checkout are:

```text
Client Frontend\config.bat
Client Frontend\start.bat
00 - Orchestrator\run.bat
```

The config UI and chat UI are separate local servers. If the config page opens
but the agents do not answer, start `Client Frontend\start.bat` as well.

## The Three Agents

### Query Agent

Use this for questions about an existing Corpus DB. It can search SQL,
full-text, embeddings and document-level evidence surfaces, then answer with
source references and page evidence.

### Ontology Agent

Use this for knowledge mining. It can build ontology lenses, compare semantic
views, attach evidence, and persist interpretive structures without overwriting
base facts.

This is powerful but expensive in tokens. A single serious ontology turn can
consume many background model and tool calls.

### Taxonomy Agent

Use this for Kernel-governed workflows:

- create empty databases
- create default or custom Semantic Releases
- run ingestion
- merge databases
- rebuild from artifacts
- reset databases
- inspect Kernel state

The Kernel owns workflow state, dialogs, blockers, confirmations and safe
resume behavior.

## Bundled Demo And Samples

The installer includes the default demo database:

```text
SampleDB\Consciousness Travel - Default Demo\Corpus\corpus.db
```

The larger Enron and purchase/invoice/shipping sample databases are intended as
separate release/sample assets. They are useful query demos, but not meant for
broad Ontology Agent mining in V1.

## Optional Extractor Tools

The release includes helper tools under:

```text
Extractor_Tools\
```

They are not part of the core ingestion pipeline. They prepare input files:

- Article Archive Extractor: URL articles to Markdown.
- YouTube Transcript Extractor: available subtitles to Markdown.
- Audio Transcription Extractor: local media files to Markdown transcripts.

Some extractors have optional dependency install scripts. See the tool folders
and the Quickstart for details.

## Documentation

The modular documentation set lives in:

```text
The Machine Doku\
```

Start here:

- `Quickstart_Handbook`
- `00_The_Design.md`
- `01_System_Overview.md`
- `02_Architecture_Map.md`
- `07_Database_Documentation.md`
- `08_Agent_Documentation.md`
- `12_Production_Handover_Notes.md`

The PDF quickstart lives in:

```text
The Machine Doku PDF\
```

## Runtime And Credentials

The Machine needs model credentials for serious use.

- The Query Agent needs an LLM provider.
- The Ontology Agent needs an LLM provider and can be token-intensive.
- Kernel taxonomy/projection workflows need Orchestrator-side credentials.
- Embeddings need embedding credentials if semantic/vector search should be
  regenerated.

Provider compatibility is not universal. Some workflows need vision-capable
models. Some model providers do not support every structured output or tool-use
shape equally well.

## Known V1 Boundaries

- Windows is the primary supported platform.
- Excel/CSV are not full V1 ingestion routes.
- Very large ontology mining is not economical in V1.
- The system is local-first, but model calls use configured external providers.
- Some Kernel workflow families are intentionally narrow and guarded.
- Error Cases and review flags are part of the evidence model, not hidden trash.

## License

The Ontology Machine software is licensed under the Apache License, Version
2.0. See:

```text
LICENSE
NOTICE
```

This software license applies to the application code and software
documentation. It does not automatically grant a general free-content license
for the bundled sample book, page images, extracted text, derived SampleDB
database artifacts, or other sample content. See:

```text
SampleDB\README.md
```

## Release Status

Current public release branch:

```text
main
```

Current release target:

```text
v1.0.0
```
