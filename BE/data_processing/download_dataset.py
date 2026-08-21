from __future__ import annotations

import argparse
import csv
import io
import os
import shutil
import sys
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path


DEFAULT_SHEET = "https://docs.google.com/spreadsheets/d/1rfn1fieTThS_Ki3SIoJ6uXOx2AhMq7wGCak6W4jZyZM/edit?gid=0#gid=0"
ESSENTIAL_GROUPS = {"keyframes", "map-keyframes", "media-info", "objects", "clip-features-32"}


@dataclass(frozen=True)
class Package:
    filename: str
    url: str
    group: str


def sheet_csv_url(sheet_url: str) -> str:
    parsed = urllib.parse.urlparse(sheet_url)
    parts = parsed.path.split("/")
    try:
        spreadsheet_id = parts[parts.index("d") + 1]
    except (ValueError, IndexError) as exc:
        raise ValueError("Google Sheet URL không hợp lệ") from exc
    query = urllib.parse.parse_qs(parsed.query)
    fragment = urllib.parse.parse_qs(parsed.fragment)
    gid = (query.get("gid") or fragment.get("gid") or ["0"])[0]
    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"


def load_packages(sheet_url: str = DEFAULT_SHEET) -> list[Package]:
    request = urllib.request.Request(sheet_csv_url(sheet_url), headers={"User-Agent": "AIC-dataset-pipeline/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        text = response.read().decode("utf-8-sig")
    packages = []
    for row in csv.DictReader(io.StringIO(text)):
        filename = (row.get("Filenames") or "").strip()
        url = (row.get("Download link") or "").strip()
        if filename and url:
            packages.append(Package(filename, url, classify_package(filename)))
    if not packages:
        raise RuntimeError("Google Sheet không có package nào hoặc chưa được chia sẻ công khai")
    return packages


def classify_package(filename: str) -> str:
    lowered = filename.casefold()
    for group in ("keyframes", "videos", "clip-features-32", "map-keyframes", "media-info", "objects"):
        if lowered.startswith(group):
            return group
    return "other"


def download(package: Package, archive_dir: Path) -> Path:
    archive_dir.mkdir(parents=True, exist_ok=True)
    destination = archive_dir / Path(package.filename).name
    partial = destination.with_suffix(destination.suffix + ".part")
    if destination.is_file():
        print(f"[skip] {destination.name}")
        return destination
    offset = partial.stat().st_size if partial.exists() else 0
    headers = {"User-Agent": "AIC-dataset-pipeline/1.0"}
    if offset:
        headers["Range"] = f"bytes={offset}-"
    request = urllib.request.Request(package.url, headers=headers)
    with urllib.request.urlopen(request, timeout=120) as response:
        append = offset > 0 and getattr(response, "status", None) == 206
        mode = "ab" if append else "wb"
        with partial.open(mode) as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
    os.replace(partial, destination)
    print(f"[downloaded] {destination.name}")
    return destination


def extract(archive: Path, data_root: Path) -> None:
    data_root.mkdir(parents=True, exist_ok=True)
    root = data_root.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            target = (root / member.filename).resolve()
            if not target.is_relative_to(root):
                raise RuntimeError(f"ZIP chứa đường dẫn không an toàn: {member.filename}")
        bundle.extractall(root)
    print(f"[extracted] {archive.name}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download official AIC packages listed in Google Sheets")
    parser.add_argument("--sheet-url", default=DEFAULT_SHEET)
    parser.add_argument("--data-root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--archive-dir", type=Path)
    parser.add_argument(
        "--groups",
        default=",".join(sorted(ESSENTIAL_GROUPS)),
        help="Comma-separated package groups; add 'videos' only when video playback is needed",
    )
    parser.add_argument("--list", action="store_true", help="Only list packages selected from the sheet")
    parser.add_argument("--extract", action="store_true", help="Extract downloaded ZIP files into data-root")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    archive_dir = args.archive_dir or args.data_root / "archives"
    selected_groups = {value.strip() for value in args.groups.split(",") if value.strip()}
    packages = [package for package in load_packages(args.sheet_url) if package.group in selected_groups]
    for package in packages:
        print(f"{package.group:18} {package.filename} {package.url}")
    if args.list:
        return 0
    if not packages:
        print("Không có package phù hợp --groups", file=sys.stderr)
        return 2
    for package in packages:
        archive = download(package, archive_dir)
        if args.extract:
            extract(archive, args.data_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
