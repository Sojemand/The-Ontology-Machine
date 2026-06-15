# Audio Transcription Extractor

Small sidecar tool for turning audio or video files into Markdown transcripts that can be used as Ontology Machine input.

It uses the OpenAI Audio Transcriptions API directly. No Python package install is required.

## Start

Run:

```bat
Start Audio Transcription Extractor.bat
```

The BAT finds the bundled Ontology Machine Python runtime relative to this folder.

## Supported Input

The first version accepts the file formats supported by the OpenAI audio upload path:

- `.mp3`
- `.mp4`
- `.mpeg`
- `.mpga`
- `.m4a`
- `.wav`
- `.webm`

The OpenAI audio upload limit is 25 MB per file. Larger files should be compressed or split before transcription.

## Output

Each transcript is written as a Markdown file with frontmatter:

- original file name
- transcript source
- model
- language
- credential source
- file hash
- transcript content hash
- transcription timestamp

With `whisper-1`, the tool writes segment timestamps when OpenAI returns them. The newer `gpt-4o-transcribe` models are available too, but they are treated as plain-text transcript models in this tool.

## Credentials

Credential mode defaults to `Auto`.

Auto tries this order:

1. API key pasted into the tool.
2. `OPENAI_API_KEY` environment variable.
3. API key saved in the Client Frontend credential store.
4. Frontend OAuth token as a last-resort test path.

`Frontend OAuth test` forces the OAuth path. If the OpenAI Audio endpoint rejects that token, use an API key instead. The frontend OAuth path is mainly built for the frontend chat backend, so it may not be accepted by the public audio endpoint.

## Recommended Defaults

- Model: `whisper-1`
- Language: `de` for German media, `en` for English media, or leave blank if you want automatic language handling.
- Save raw JSON: enabled, because it keeps the model output auditable.

## Corpus Use

The Markdown output can be dropped into an Artifact Tree `Input` folder or used as input for a new Kernel/Orchestrator creation run.
