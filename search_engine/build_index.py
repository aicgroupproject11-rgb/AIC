"""Backward-compatible entry point for the original student branch."""

import sys

from BE.search_engine.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["build-index", *sys.argv[1:]]))
