from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VENDOR_PYTHON_ZIP = PROJECT_ROOT / "vendor" / "python" / "cpython-3.11.9-win_amd64.zip"
RUNTIME_WHEELHOUSE = PROJECT_ROOT / "runtime" / "wheelhouse"
DEV_WHEELHOUSE = PROJECT_ROOT / "dev-tests" / "wheelhouse"
RUNTIME_LOCKFILE = PROJECT_ROOT / "runtime" / "requirements.lock.txt"
DEV_LOCKFILE = PROJECT_ROOT / "dev-tests" / "requirements.lock.txt"

TEXT_SUFFIXES = {
    ".bat",
    ".cfg",
    ".cmd",
    ".ini",
    ".json",
    ".md",
    ".ps1",
    ".pth",
    ".py",
    ".pyi",
    ".txt",
    ".yaml",
    ".yml",
}
SKIP_DIR_NAMES = {".git", ".pytest_cache", ".pytest-tmp", ".tmp", "__pycache__", "output", "state", "tests"}
HOME_PATH = Path.home().resolve()
WORKSPACE_ROOT = PROJECT_ROOT.parents[3]
HOME_REGEX = re.escape(str(HOME_PATH))
ABSOLUTE_PATH_PATTERNS = (
    re.compile(HOME_REGEX, re.IGNORECASE),
    re.compile(HOME_REGEX + re.escape(r"\AppData\Local\Programs\Python\Python") + r"\d+", re.IGNORECASE),
    re.compile(HOME_REGEX + re.escape(r"\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.") + r".+", re.IGNORECASE),
    re.compile(re.escape(str(WORKSPACE_ROOT / ".venv")), re.IGNORECASE),
)


@dataclass(frozen=True)
class EnvironmentSpec:
    name: str
    root: Path
    lockfile: Path
    wheelhouses: tuple[Path, ...]

    @property
    def python_exe(self) -> Path:
        return self.root / "python.exe"


RUNTIME_SPEC = EnvironmentSpec(
    name="runtime",
    root=PROJECT_ROOT / "runtime" / "python",
    lockfile=RUNTIME_LOCKFILE,
    wheelhouses=(RUNTIME_WHEELHOUSE,),
)
DEV_SPEC = EnvironmentSpec(
    name="dev",
    root=PROJECT_ROOT / "dev-tests" / ".venv",
    lockfile=DEV_LOCKFILE,
    wheelhouses=(DEV_WHEELHOUSE,),
)


def canonicalize_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def parse_lockfile(path: Path) -> dict[str, str]:
    locked: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "==" not in line:
            raise ValueError(f"Lockfile-Zeile ist nicht gepinnt: {line}")
        name, version = line.split("==", 1)
        locked[canonicalize_name(name)] = version.strip()
    return locked


def parse_wheelhouse(path: Path) -> dict[str, str]:
    wheels: dict[str, str] = {}
    for wheel_path in path.glob("*.whl"):
        match = re.match(r"(?P<name>.+)-(?P<version>[^-]+)(?:-[^-]+)?-[^-]+-[^-]+-[^-]+\.whl$", wheel_path.name)
        if match:
            wheels[canonicalize_name(match.group("name"))] = match.group("version")
    return wheels


def scan_text_files(root: Path, *, skip_dir_names: set[str] | None = None) -> list[str]:
    effective_skip_dir_names = skip_dir_names or SKIP_DIR_NAMES
    issues: list[str] = []
    for path in root.rglob("*"):
        if any(part in effective_skip_dir_names for part in path.parts) or not path.is_file():
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="utf-8", errors="ignore")
        if any(pattern.search(content) for pattern in ABSOLUTE_PATH_PATTERNS):
            issues.append(f"{path}: hostgebundener Pfad gefunden")
    return issues
