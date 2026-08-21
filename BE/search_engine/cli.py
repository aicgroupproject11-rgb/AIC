from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .builder import BuildOptions, build_search_index
from .indexer import DEFAULT_INDEX_DIR, HybridSearchIndex
from .kis import search


DEFAULT_DATA_ROOT = Path(__file__).resolve().parent.parent / "data_processing"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m search_engine.cli",
        description="Build and query the AIC hybrid domain/BoW/R-tree index.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build-index", help="Build all search artifacts")
    build.add_argument("--data-root", type=Path, default=Path(os.getenv("KIS_DATA_ROOT", DEFAULT_DATA_ROOT)))
    build.add_argument("--manifest", type=Path)
    build.add_argument("--index-dir", type=Path, default=Path(os.getenv("KIS_INDEX_ROOT", DEFAULT_INDEX_DIR)))
    build.add_argument("--taxonomy", type=Path)
    build.add_argument("--pca-dim", type=int, default=24)
    build.add_argument("--pca-sample-size", type=int, default=50_000)
    build.add_argument("--domains-per-frame", type=int, default=2)
    build.add_argument("--object-min-score", type=float, default=0.25)

    inspect = subparsers.add_parser("inspect-index", help="Print index metadata")
    inspect.add_argument("--index-dir", type=Path, default=Path(os.getenv("KIS_INDEX_ROOT", DEFAULT_INDEX_DIR)))

    query = subparsers.add_parser("search", help="Run a CLI search smoke test")
    query.add_argument("query")
    query.add_argument("--collection", action="append", default=[])
    query.add_argument("--top-k", type=int, default=10)
    query.add_argument("--index-dir", type=Path, default=Path(os.getenv("KIS_INDEX_ROOT", DEFAULT_INDEX_DIR)))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "build-index":
        options = BuildOptions(
            pca_dimensions=args.pca_dim,
            pca_sample_size=args.pca_sample_size,
            domains_per_frame=args.domains_per_frame,
            object_min_score=args.object_min_score,
        )
        metadata = build_search_index(
            data_root=args.data_root,
            manifest_path=args.manifest,
            index_dir=args.index_dir,
            taxonomy_path=args.taxonomy,
            options=options,
        )
        print(json.dumps(metadata, ensure_ascii=False, indent=2))
        return 0
    if args.command == "inspect-index":
        index = HybridSearchIndex.load(args.index_dir)
        print(json.dumps(index.metadata, ensure_ascii=False, indent=2))
        index.close()
        return 0
    if args.command == "search":
        os.environ["KIS_INDEX_ROOT"] = str(args.index_dir.resolve())
        results = search(query=args.query, collection_ids=args.collection, top_k=args.top_k)
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
