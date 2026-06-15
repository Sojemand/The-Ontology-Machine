import json
import os
import pathlib
import sys
from urllib.parse import unquote, urlparse

from .errors import deny

BLOCKED_IMPORT_ROOTS = {
    "asyncio",
    "ctypes",
    "ftplib",
    "multiprocessing",
    "requests",
    "subprocess",
    "telnetlib",
    "webbrowser",
    "winreg",
}

ALLOWED_ENV_VARS = {
    "COMSPEC",
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "WINDIR",
    "MIN_AGENT_ROOT_DIR",
    "MIN_AGENT_DATA_DIR",
    "MIN_AGENT_DB_PATH",
    "MIN_AGENT_WORKBENCH_ALLOWED_ROOTS",
    "MIN_AGENT_WORKBENCH_ALLOWED_FILES",
}

ROOT_DIR = pathlib.Path(os.environ.get("MIN_AGENT_ROOT_DIR") or os.getcwd()).resolve()


def load_scope_paths(name: str):
    raw = os.environ.get(name, "[]")
    try:
        values = json.loads(raw)
    except Exception:
        values = []
    return [pathlib.Path(str(value)).resolve() for value in values if value]


ALLOWED_ROOTS = load_scope_paths("MIN_AGENT_WORKBENCH_ALLOWED_ROOTS")
ALLOWED_FILES = set(load_scope_paths("MIN_AGENT_WORKBENCH_ALLOWED_FILES"))
INTERNAL_ALLOWED_ROOTS = [pathlib.Path(sys.executable).resolve().parent]


def is_relative_to(candidate: pathlib.Path, base: pathlib.Path) -> bool:
    try:
        candidate.relative_to(base)
        return True
    except ValueError:
        return False


def resolve_candidate_path(value) -> pathlib.Path:
    if isinstance(value, int):
        deny("Python workbench blockiert Dateideskriptoren.")
    try:
        raw = os.fspath(value)
    except TypeError:
        deny("Python workbench braucht einen gueltigen Dateipfad.")
    if raw is None:
        deny("Python workbench braucht einen gueltigen Dateipfad.")

    normalized = str(raw).strip()
    if not normalized:
        deny("Python workbench braucht einen gueltigen Dateipfad.")
    if normalized.startswith("\\\\"):
        deny("Python workbench blockiert Netzwerk- und UNC-Pfade.")
    if "://" in normalized or normalized.startswith("file:"):
        parsed = urlparse(normalized)
        if parsed.scheme != "file":
            deny("Python workbench blockiert Netzwerk- und URI-Pfade.")
        normalized = unquote(parsed.path or "")
        if normalized.startswith("/") and len(normalized) > 3 and normalized[2] == ":":
            normalized = normalized[1:]

    candidate = pathlib.Path(normalized)
    if not candidate.is_absolute():
        candidate = ROOT_DIR / candidate
    resolved = candidate.resolve(strict=False)
    if resolved in ALLOWED_FILES:
        return resolved
    if any(is_relative_to(resolved, allowed_root) for allowed_root in ALLOWED_ROOTS):
        return resolved
    if any(is_relative_to(resolved, allowed_root) for allowed_root in INTERNAL_ALLOWED_ROOTS):
        return resolved
    deny("Python workbench darf nur corpus-nahe Dateien und Verzeichnisse unter dem Frontend-Root lesen.")


def ensure_read_only_mode(mode) -> str:
    normalized = str(mode or "r")
    if any(flag in normalized for flag in ("w", "a", "x", "+")):
        deny("Python workbench ist read-only.")
    return normalized
