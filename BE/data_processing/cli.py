from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .pipeline import build_collection, build_manifest, scan_dataset


DEFAULT_ROOT = Path(__file__).resolve().parent


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="python -m data_processing.cli")
    commands = root.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("scan", help="Check folders and cross-source video IDs")
    scan.add_argument("--data-root", type=Path, default=Path(os.getenv("KIS_DATA_ROOT", DEFAULT_ROOT)))
    scan.add_argument("--deep", action="store_true", help="Also compare keyframe/map/CLIP counts")
    manifest = commands.add_parser("build-manifest", help="Build canonical manifest.csv")
    manifest.add_argument("--data-root", type=Path, default=Path(os.getenv("KIS_DATA_ROOT", DEFAULT_ROOT)))
    manifest.add_argument("--output", type=Path)
    collection = commands.add_parser("build-collection", help="Build collection.json from manifest")
    collection.add_argument("--manifest", type=Path, default=DEFAULT_ROOT / "manifest.csv")
    collection.add_argument("--output", type=Path)
    prepare = commands.add_parser("prepare", help="Deep validation + manifest + collection")
    prepare.add_argument("--data-root", type=Path, default=Path(os.getenv("KIS_DATA_ROOT", DEFAULT_ROOT)))
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "scan":
        report = scan_dataset(args.data_root, deep=args.deep)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        return 0 if report.valid else 1
    if args.command == "build-manifest":
        print(json.dumps(build_manifest(args.data_root, args.output), ensure_ascii=False, indent=2))
        return 0
    if args.command == "build-collection":
        print(json.dumps(build_collection(args.manifest, args.output), ensure_ascii=False, indent=2))
        return 0
    if args.command == "prepare":
        report = scan_dataset(args.data_root, deep=True)
        if not report.valid:
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
            return 1
        manifest = build_manifest(args.data_root)
        collection = build_collection(Path(manifest["output"]))
        print(json.dumps({"scan": report.to_dict(), "manifest": manifest, "collection": collection}, ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
