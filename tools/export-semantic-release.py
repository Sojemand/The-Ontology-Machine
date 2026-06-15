from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PIPELINE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NORMALIZER_ROOT = PIPELINE_ROOT / "04 - Normalizer"


def export_semantic_release(
    output_path: str | Path,
    *,
    normalizer_root: str | Path | None = None,
    target_locale: str | None = None,
) -> dict[str, object]:
    root = Path(normalizer_root) if normalizer_root is not None else DEFAULT_NORMALIZER_ROOT
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from normalizer_vision.semantic_release import publish_semantic_release

    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    return publish_semantic_release(root, target_path, target_locale=target_locale)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Publish the current Normalizer semantic release to an explicit output path.")
    parser.add_argument("output_path", help="Target JSON file path for the published semantic release.")
    parser.add_argument(
        "--normalizer-root",
        default=str(DEFAULT_NORMALIZER_ROOT),
        help="Normalizer project root to publish from. Defaults to the pipeline's '04 - Normalizer' directory.",
    )
    parser.add_argument("--target-locale", help="Optional runtime locale to export instead of the release default.")
    args = parser.parse_args(argv)

    release = export_semantic_release(
        args.output_path,
        normalizer_root=args.normalizer_root,
        target_locale=args.target_locale,
    )
    print(
        json.dumps(
            {
                "output_path": str(Path(args.output_path)),
                "release_id": release.get("release_id"),
                "release_version": release.get("release_version"),
                "fingerprint": release.get("fingerprint"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
