from __future__ import annotations

import json
import subprocess
import sys
import sysconfig
from dataclasses import dataclass
from pathlib import Path


_PYTHON_QUERY = (
    "import json, sys, sysconfig; "
    "print(json.dumps({"
    "'base_prefix': sys.base_prefix, "
    "'executable': sys.executable, "
    "'platform': sys.platform, "
    "'scripts': sysconfig.get_path('scripts'), "
    "'stdlib': sysconfig.get_path('stdlib'), "
    "'version': list(sys.version_info[:3])"
    "}))"
)


@dataclass(frozen=True)
class PythonLayout:
    python_exe: Path
    home: Path
    stdlib_dir: Path
    scripts_dir: Path
    version_info: tuple[int, int, int]
    platform: str

    @property
    def version_text(self) -> str:
        return ".".join(str(part) for part in self.version_info)


def query_python_layout(python_exe: str | Path) -> PythonLayout:
    completed = subprocess.run(
        [str(python_exe), "-c", _PYTHON_QUERY],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    data = json.loads(completed.stdout)
    return PythonLayout(
        python_exe=Path(data["executable"]).resolve(),
        home=Path(data["base_prefix"]).resolve(),
        stdlib_dir=Path(data["stdlib"]).resolve(),
        scripts_dir=Path(data["scripts"]).resolve(),
        version_info=tuple(int(part) for part in data["version"]),
        platform=str(data["platform"]),
    )


def runtime_python(runtime_dir: str | Path, *, platform: str | None = None) -> Path:
    root = Path(runtime_dir)
    target_platform = platform or sys.platform
    ext = ".exe" if target_platform == "win32" else ""
    candidates = (
        root / f"python{ext}",
        root / "Scripts" / f"python{ext}",
        root / "bin" / "python",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def site_packages_dir(
    runtime_dir: str | Path,
    *,
    version_info: tuple[int, int, int] | None = None,
    platform: str | None = None,
) -> Path:
    root = Path(runtime_dir)
    target_platform = platform or sys.platform
    if target_platform == "win32":
        return root / "Lib" / "site-packages"
    if version_info is None:
        raise ValueError("version_info is required for non-Windows site-packages paths")
    return root / "lib" / f"python{version_info[0]}.{version_info[1]}" / "site-packages"
