# Ontology Machine SampleDB

This folder contains bundled sample data for **The Ontology Machine**.

The current default demo is:

```text
Consciousness Travel - Default Demo/
```

It contains a prepared Ontology Machine Artifact Tree and Corpus DB for the book **Bewusstseinsreisen**.

## Included Work

**Bewusstseinsreisen** is an original book written by **Norman Weiss**, the author and rights holder of this sample material as well as the creator of the Ontology Machine.

The included PDF, rendered page images, extracted text, structured JSON, normalized artifacts, embeddings, ontology data, semantic release files, and corpus database are derived from that book and are included only so that users can test, inspect, and understand The Ontology Machine with a real prepared corpus.

## License And Use Restriction

The sample book content is **not** released under a general free-content license.

Permission is granted only for the following limited purpose:

- using this bundled SampleDB as part of The Ontology Machine;
- opening and querying the included Corpus DB in the Client Frontend;
- inspecting the Artifact Tree, page images, extracted data, semantic release, embeddings, and ontology lenses as a demo of the software;
- rebuilding or experimenting with this sample locally for evaluation of The Ontology Machine.

No permission is granted to:

- redistribute the book text, PDF, page images, extracted text, or derived database as a standalone dataset;
- republish the book or substantial excerpts outside The Ontology Machine sample context;
- use the book content as training data for unrelated models, datasets, products, or services;
- sell, sublicense, or repackage the content independently from The Ontology Machine;
- imply that the book content itself is open source, public domain, or freely licensed.

The license for The Ontology Machine software and the license for this sample content are separate. Any software license that applies to the application code does **not** automatically apply to the book content or its derived sample database artifacts.

## Default Demo Contents

```text
SampleDB/
  Consciousness Travel - Default Demo/
    Corpus/
      corpus.db
    Documents/
      originals/
      page_images/
      raw_extracts/
      structured/
      normalized/
      validation/
      logs/
    Error Cases/
    Input/
    Semantic Release/
```

The prepared demo currently contains:

- 1 source document: `Bewusstseinsreisen - Version 2.pdf`
- 102 materialized page-level corpus records
- 102 stored page images
- 102 document embeddings
- 993 document embedding chunks
- 226 ontology embedding chunks
- 1 active custom Semantic Release
- 1 active primary ontology lens: `Theory of Mind Lens for Bewusstseinsreisen`
- a refreshed Base Graph with source-document pages, structural units, structural relations, and source-document classifications

## Intended Purpose

This SampleDB exists to give users an immediate, working corpus after installation. It is meant to demonstrate:

- page-level materialization;
- source-document grouping;
- image-backed evidence;
- semantic release activation;
- embeddings and semantic search;
- ontology lenses and knowledge mining;
- Query Agent and Ontology Agent behavior on a real text.

## Source Contract

`SampleDB` is an immutable bundled demo and regression payload. It is not a
runtime state directory and must not be treated as the user's active writable
corpus during normal operation.

The prepared Artifact Tree, Corpus DB, page images, derived JSON, logs, and
Semantic Release files are versioned together so installers, tests, and fresh
local runs have a stable demo corpus. Changes to these files should be
intentional fixture regeneration or sample-content maintenance, not incidental
output from an app run.

Live user corpora, mutable app state, credentials, model catalogs, chats, and
temporary pipeline output belong in the owner-specific runtime/app-home paths,
not in `SampleDB`.

## Attribution

When referring to this sample outside the local installation context, describe it as:

> **Bewusstseinsreisen SampleDB for The Ontology Machine**, based on an original book by Norman Weiss. Included only as a bundled software demo corpus.

All rights in the book content remain reserved by the author except for the limited SampleDB use described above.
