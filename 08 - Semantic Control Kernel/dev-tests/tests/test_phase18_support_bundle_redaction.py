from __future__ import annotations

import json
from pathlib import Path

from semantic_control_kernel.debug.redaction import RedactionEngine, RedactionProfile


MODULE_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = MODULE_ROOT / "dev-tests" / "fixtures" / "phase18" / "redaction_payloads" / "payload.json"


def test_redaction_engine_removes_secrets_paths_raw_payloads_and_tracebacks(tmp_path: Path) -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    state_root = tmp_path / "state"
    state_root.mkdir(parents=True, exist_ok=True)

    engine = RedactionEngine(state_root=state_root)
    redacted, stats = engine.redact(payload, profile_id=RedactionProfile.SUPPORT_SAFE_V1)
    serialized = json.dumps(redacted, sort_keys=True)

    assert "sk-test-super-secret" not in serialized
    assert "secret-token" not in serialized
    assert "full prompt body should not leak" not in serialized
    assert "full raw provider output" not in serialized
    assert "full database row payload" not in serialized
    assert "C:\\Users\\Norma\\Desktop\\Secret Folder\\document.pdf" not in serialized
    assert "Traceback (most recent call last):" not in serialized
    assert stats.redacted_secret_counts
    assert stats.redacted_field_counts
    assert stats.redacted_path_counts


def test_redaction_engine_redacts_mixed_secret_path_strings_and_traceback_tails(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    state_root.mkdir(parents=True, exist_ok=True)
    payload = {
        "mixed": "failure used sk-test-mixed-secret at C:\\Users\\Norma\\Desktop\\Secret Folder\\document.pdf",
        "traceback": (
            "Traceback (most recent call last):\n"
            "  File \"service.py\", line 1, in <module>\n"
            "ValueError: sk-test-traceback-secret from C:\\Users\\Norma\\Desktop\\Trace\\raw.txt"
        ),
    }

    redacted, stats = RedactionEngine(state_root=state_root).redact(
        payload,
        profile_id=RedactionProfile.SUPPORT_SAFE_V1,
    )
    serialized = json.dumps(redacted, sort_keys=True)

    assert "sk-test-mixed-secret" not in serialized
    assert "sk-test-traceback-secret" not in serialized
    assert "C:\\Users\\Norma\\Desktop\\Secret Folder\\document.pdf" not in serialized
    assert "C:\\Users\\Norma\\Desktop\\Trace\\raw.txt" not in serialized
    assert "[redacted traceback]" in serialized
    assert stats.redacted_secret_counts["openai_key"] == 2
    assert stats.redacted_path_counts["external_absolute"] == 2
