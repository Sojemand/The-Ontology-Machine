from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable


def main_impl(
    *,
    default_plugin_dir: Path,
    resolve_paths: Callable[[Path], Any],
    default_runtime_dir: Callable[[Path], Path],
    download_wheelhouse: Callable[..., dict[str, Any]],
    install_into_runtime: Callable[..., None],
    bootstrap: Callable[..., dict[str, Any]],
) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("bootstrap", "download-wheelhouse", "install-runtime"))
    parser.add_argument("--plugin-dir", default=str(default_plugin_dir))
    parser.add_argument("--runtime-dir", default="")
    parser.add_argument("--base-python", default="")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--refresh-wheelhouse", action="store_true")
    parser.add_argument("--archive-wheelhouse", action="store_true")
    args = parser.parse_args()
    plugin_dir = Path(args.plugin_dir).resolve()
    runtime_dir = Path(args.runtime_dir).resolve() if args.runtime_dir else default_runtime_dir(plugin_dir)
    paths = resolve_paths(plugin_dir)
    if args.command == "download-wheelhouse":
        payload = download_wheelhouse(paths, offline=args.offline, refresh=args.refresh_wheelhouse)
    elif args.command == "install-runtime":
        install_into_runtime(paths, runtime_dir, offline=args.offline)
        payload = {"runtime_dir": str(runtime_dir), "vendor_dir": str(paths.vendor_dir)}
    else:
        payload = bootstrap(
            plugin_dir,
            runtime_dir,
            base_python=Path(args.base_python).resolve() if args.base_python else None,
            offline=args.offline,
            refresh_wheelhouse=args.refresh_wheelhouse,
            archive_wheelhouse=args.archive_wheelhouse,
        )
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    return 0
