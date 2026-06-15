"""Surface stage for the Edit Suite CLI entrypoint."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="edit_suite",
        description="Vision Pipeline Edit Suite",
    )
    return parser
