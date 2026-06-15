# GitHub Release Checklist

This is the practical browser checklist for publishing The Ontology Machine
v1.0.0.

## 1. Prepare The Repository

Open the repository in GitHub:

```text
https://github.com/Sojemand/The-Ontology-Machine
```

Recommended before release:

1. Keep the repository name as `The-Ontology-Machine`.
2. Make sure the repository is public.
3. Add repository description:

```text
Local-first Windows knowledge mining system for evidence-bound corpus databases, ontology lenses and LLM-assisted document analysis.
```

4. Add topics:

```text
ontology
knowledge-mining
semantic-search
sqlite
local-first
llm-agents
document-processing
corpus-analysis
research-tools
windows
```

5. Confirm license display.

The software is licensed under Apache License 2.0 through the root `LICENSE`
file. The bundled SampleDB/book content remains separately restricted through
`SampleDB\README.md`.

## 2. Create The Release

On GitHub:

1. Open the repository.
2. Click `Releases`.
3. Click `Draft a new release`.
4. Create a new tag:

```text
v1.0.0
```

5. Target branch:

```text
main
```

6. Release title:

```text
The Ontology Machine v1.0.0
```

7. Paste the content from:

```text
RELEASE_NOTES_v1.0.0.md
```

8. Upload release assets:

```text
dist\all-in-one\installer\OntologyMachine-AllInOne-Setup-2026-06-15.exe
SHA256SUMS.txt
The Machine Doku PDF\Quickstart_Handbook.pdf
```

9. Publish release.

## 3. Optional Sample DB Assets

If you want to publish the official large sample DBs, upload them as separate
release assets or a separate sample release.

Do not put large DBs directly into the Git repository.

## 4. Profile README

If you want a GitHub profile README:

1. Create a public repository named exactly like your GitHub username.
2. Put `PROFILE_README_DRAFT.md` content into that repo as `README.md`.
3. Replace `<repo-name-after-rename>` with the final repository name.
4. Pin The Ontology Machine repository on your GitHub profile.

## 5. Final Public Links

After renaming and publishing, the public links should look like:

```text
Repository:
https://github.com/Sojemand/The-Ontology-Machine

Latest release:
https://github.com/Sojemand/The-Ontology-Machine/releases/latest
```
