"""Materialize default mutable prompt-bundle files for installed app homes."""
from __future__ import annotations

import argparse

from .models import atomic_text_write
from .prompts.bundle import PROMPT_BUNDLE_FILES, load_prompt_bundle
from .runtime_paths import RUNTIME_HOME_ENV, ensure_config_dir, resolve_runtime_paths


def ensure_default_app_config(paths) -> None:
    ensure_config_dir(paths)
    defaults = load_prompt_bundle(paths.config_dir)
    bundle_dir = paths.config_dir / "prompt_bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    for field_name, file_name in PROMPT_BUNDLE_FILES.items():
        target = bundle_dir / file_name
        if not target.exists():
            atomic_text_write(target, defaults[field_name] + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-home", default="")
    args = parser.parse_args(argv)
    env = {RUNTIME_HOME_ENV: args.app_home} if str(args.app_home).strip() else None
    ensure_default_app_config(resolve_runtime_paths(env))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
