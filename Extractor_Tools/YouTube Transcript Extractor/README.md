# YouTube Transcript Extractor

<!-- cspell:words ytdlp frontmatter -->

Small local sidecar tool for turning YouTube subtitle tracks into Markdown
transcripts that can be used as Ontology Machine input.

It does not transcribe audio. It only reads subtitle tracks that YouTube already
exposes for a video.

## Start

First install the local dependency once:

```text
Install yt-dlp.bat
```

Then double-click:

```text
Start YouTube Transcript Extractor.bat
```

Paste one or more YouTube video URLs into the text box, choose an output folder,
and start extraction.

The default `Auto` mode is meant to hide the cookie mess:

1. Try normal subtitle access first.
2. If YouTube blocks auto subtitles, use a local `cookies.txt` if one exists.
3. If no `cookies.txt` exists, try the first detected browser session.

The repository cannot include a real `cookies.txt`. Real cookies are private
browser/session data. The folder contains `cookies.example.txt` only as a safe
placeholder. Export your own cookies in Netscape cookie-file format, name the
exported file `cookies.txt`, and place it next to this README. The GUI also has
a `Cookie help` button with the same short explanation. Most users should not
need this unless YouTube keeps blocking auto subtitles.

If the browser cookie database is locked, close the browser completely and retry.
Brave is not the same cookie store as Chrome, even though both are
Chromium-based.

The launcher first uses the tool-local `.venv` if present, then finds the
bundled Ontology Machine Python runtimes relative to the Machine root. It does
not depend on a host Python installation. The `YouTube Transcript Extractor`
folder must stay inside the Ontology Machine `Extractor_Tools` folder.

## Output

For each video the tool writes one `.md` file with YAML-style frontmatter:

```md
---
source_url: "https://www.youtube.com/watch?v=..."
source_platform: "youtube"
source_channel: "tagesschau"
title: "tagesschau 20:00 Uhr"
published_at: "2026-06-13"
duration_seconds: 900
video_id: "..."
transcript_source: "youtube_subtitles"
subtitle_language: "de"
url_hash: "sha256:..."
content_hash: "sha256:..."
extractor: "yt-dlp-subtitles"
raw_subtitles_path: "..."
---

# tagesschau 20:00 Uhr

## Transcript

[00:00:00.000 - 00:00:04.000] Guten Abend...
```

The output folder also receives:

- `transcript_report.csv`
- `failed_urls.csv` if one or more URLs failed
- `raw_subtitles/` if raw subtitle saving is enabled

## Scope

This first version assumes the video has a readable subtitle track. It can use
manual YouTube subtitles and, if enabled, YouTube auto subtitles. It does not
download video files and does not run Whisper or another speech-to-text model.

Cookie support is optional and only exists to make YouTube's subtitle endpoint
less brittle for videos where anonymous auto-subtitle requests get rate-limited.
`Auto` mode keeps the simple path simple and only uses cookie-backed access after
standard access fails.

On Windows, Chromium-based browsers can lock their cookie database while they
are running. If cookie copying fails, close the selected browser completely,
including background processes, and retry. If that still fails, export a
`cookies.txt` file and use `Cookie mode = cookies.txt file`.

The timestamped Markdown is meant to preserve evidence anchors for later corpus
ingestion and ontology work.

## CLI Mode

The GUI is the intended path, but the same tool can run from the command line:

```bat
python youtube_transcript_extractor.py --cli --urls-file urls.txt --output-dir output --language de
```

Use browser cookies from CLI:

```bat
python youtube_transcript_extractor.py --cli --url https://www.youtube.com/watch?v=... --output-dir output --cookie-mode auto
```

Use an exported cookie file:

```bat
python youtube_transcript_extractor.py --cli --url https://www.youtube.com/watch?v=... --output-dir output --cookie-mode file --cookies-file cookies.txt
```

## Notes

This is a local archive preparation tool. Respect platform terms and source
rights. Subtitle availability depends on YouTube and on the channel/video.
