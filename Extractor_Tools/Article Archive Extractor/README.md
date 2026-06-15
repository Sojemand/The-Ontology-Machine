# Article Archive Extractor

<!-- cspell:words frontmatter trafilatura venv -->

Small local sidecar tool for turning article URLs into Markdown files that can
be used as Ontology Machine input.

It is intentionally not a new Ontology Machine module. It only prepares source
files.

## Start

Double-click:

```text
Start Article Archive Extractor.bat
```

Paste one or more article URLs into the text box, choose an output folder, and
start extraction.

The launcher first uses a local `.venv` if present, then finds the bundled
Ontology Machine Python runtimes relative to the Machine root. It does not
depend on a host Python installation. The `Article Archive Extractor` folder
must stay inside the Ontology Machine `Extractor_Tools` folder.

## Output

For each article the tool writes one `.md` file with YAML-style frontmatter:

```md
---
source_url: "https://example.org/article"
source_domain: "example.org"
title: "Article title"
published_at: "2026-06-13"
fetched_at: "2026-06-13T12:00:00+00:00"
url_hash: "sha256:..."
content_hash: "sha256:..."
extractor: "trafilatura"
raw_html_path: null
---

# Article title

Article text...
```

The output folder also receives:

- `extraction_report.csv`
- `failed_urls.csv`
- `raw_html/` if raw HTML saving is enabled

## Optional Better Extraction

The tool works without external packages through a conservative HTML fallback.
For better article extraction, install the optional dependency:

```bat
Install Optional Trafilatura.bat
```

This creates a local `.venv` inside the tool folder using the bundled Ontology
Machine Python runtime, then installs `trafilatura` there. It does not modify the
Machine module runtimes. `trafilatura` is usually better at removing navigation,
share boxes, related links and other page chrome.

## CLI Mode

The GUI is the intended path, but the same tool can run from the command line:

```bat
python article_archive_extractor.py --cli --urls-file urls.txt --output-dir output --save-raw-html
```

## Notes

This is a local archive preparation tool. Respect source rights and site terms.
The Markdown files preserve source URL, fetch time, URL hash and content hash so
the corpus remains source-bound.
