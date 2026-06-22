from __future__ import annotations

import sys
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(MODULE_ROOT))

from youtube_transcript_core import _parse_subtitle_text, _select_subtitle  # noqa: E402


ROLLING_AUTO_VTT = """WEBVTT

00:00:18.070 --> 00:00:18.080
Heute im Studio Romi Hiller.

00:00:18.080 --> 00:00:19.510
Heute im Studio Romi Hiller. Einen schoenen guten Abend. Ich begruesse

00:00:19.510 --> 00:00:19.520
Einen schoenen guten Abend. Ich begruesse

00:00:19.520 --> 00:00:21.509
Einen schoenen guten Abend. Ich begruesse Sie zur Tagesschau.
"""


def test_manual_subtitles_keep_vtt_preference() -> None:
    info = {
        "subtitles": {
            "de": [
                {"ext": "json3", "url": "manual-json3"},
                {"ext": "vtt", "url": "manual-vtt"},
            ]
        },
        "automatic_captions": {
            "de": [
                {"ext": "json3", "url": "auto-json3"},
            ]
        },
    }

    language, source, entry = _select_subtitle(info, "de", allow_auto=True)

    assert language == "de"
    assert source == "youtube_subtitles"
    assert entry["url"] == "manual-vtt"


def test_auto_subtitles_prefer_json3_over_vtt() -> None:
    info = {
        "subtitles": {},
        "automatic_captions": {
            "de": [
                {"ext": "vtt", "url": "auto-vtt"},
                {"ext": "json3", "url": "auto-json3"},
            ]
        },
    }

    language, source, entry = _select_subtitle(info, "de", allow_auto=True)

    assert language == "de"
    assert source == "youtube_auto_subtitles"
    assert entry["url"] == "auto-json3"


def test_auto_vtt_fallback_removes_rolling_caption_updates() -> None:
    segments = _parse_subtitle_text(ROLLING_AUTO_VTT, "vtt", subtitle_source="youtube_auto_subtitles")

    assert [segment.text for segment in segments] == [
        "Heute im Studio Romi Hiller. Einen schoenen guten Abend. Ich begruesse",
        "Sie zur Tagesschau.",
    ]
    assert all(segment.end != "00:00:18.080" and segment.end != "00:00:19.520" for segment in segments)


def test_manual_vtt_is_not_auto_cleaned() -> None:
    segments = _parse_subtitle_text(ROLLING_AUTO_VTT, "vtt", subtitle_source="youtube_subtitles")

    assert [segment.text for segment in segments] == [
        "Heute im Studio Romi Hiller.",
        "Heute im Studio Romi Hiller. Einen schoenen guten Abend. Ich begruesse",
        "Einen schoenen guten Abend. Ich begruesse",
        "Einen schoenen guten Abend. Ich begruesse Sie zur Tagesschau.",
    ]
