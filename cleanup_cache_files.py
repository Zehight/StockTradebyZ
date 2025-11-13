#!/usr/bin/env python3
"""
Utility to prune dated cache/report artifacts.

Files are deleted only when:
  1. The filename contains a date (YYYYMMDD or YYYY-MM-DD).
  2. The file extension matches the allowed list.
  3. The extracted date is older than the configured retention window.

Examples:
    python cleanup_cache_files.py --path cache --days 5 --extensions .json .csv --skip-token _latest
    python cleanup_cache_files.py --path reports --days 5 --extensions .html .json
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

DATE_PATTERNS = [
    re.compile(r"(\d{4})-(\d{2})-(\d{2})"),  # e.g. report-2025-11-07.html
    re.compile(r"(\d{4})(\d{2})(\d{2})"),    # e.g. picks_xxx_20250907.json
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Delete dated files older than N days.")
    parser.add_argument("--path", required=True, type=Path, help="Target directory to scan.")
    parser.add_argument(
        "--days",
        type=int,
        default=5,
        help="Retention window in days (files strictly older than this value will be removed).",
    )
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=[".json"],
        help="File extensions to include (case-insensitive).",
    )
    parser.add_argument(
        "--skip-token",
        dest="skip_tokens",
        action="append",
        default=["latest"],
        help="Filename substrings to skip. Can be provided multiple times.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without removing files.",
    )
    return parser.parse_args()


def normalize_extensions(exts: Sequence[str]) -> Sequence[str]:
    return tuple(ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in exts)


def extract_date_from_filename(filename: str) -> Optional[dt.date]:
    for pattern in DATE_PATTERNS:
        matches = list(pattern.finditer(filename))
        if not matches:
            continue
        year, month, day = (int(part) for part in matches[-1].groups())
        try:
            return dt.date(year, month, day)
        except ValueError:
            return None
    return None


def should_skip(path: Path, skip_tokens: Sequence[str]) -> bool:
    lowercase_name = path.name.lower()
    return any(token.lower() in lowercase_name for token in skip_tokens)


def gather_candidates(
    root: Path, extensions: Sequence[str], skip_tokens: Sequence[str]
) -> Iterable[Tuple[Path, dt.date]]:
    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in extensions:
            continue
        if should_skip(file_path, skip_tokens):
            continue
        extracted_date = extract_date_from_filename(file_path.name)
        if not extracted_date:
            continue
        yield file_path, extracted_date


def cleanup(
    root: Path, keep_days: int, extensions: Sequence[str], skip_tokens: Sequence[str], dry_run: bool
) -> Tuple[int, List[Path]]:
    today = dt.datetime.now().date()
    deleted = 0
    deleted_paths: List[Path] = []
    for path, file_date in gather_candidates(root, extensions, skip_tokens):
        age_days = (today - file_date).days
        if age_days > keep_days:
            print(f"[CLEANUP] {path} -> dated {file_date} ({age_days} days old)")
            if not dry_run:
                path.unlink(missing_ok=True)
            deleted += 1
            deleted_paths.append(path)
    print(
        f"[CLEANUP] Completed scanning {root}. "
        f"Removed {deleted} file(s). Dry-run: {'yes' if dry_run else 'no'}."
    )
    return deleted, deleted_paths


def main() -> None:
    args = parse_args()
    target_dir: Path = args.path
    if not target_dir.exists():
        print(f"[CLEANUP] Directory {target_dir} does not exist. Nothing to do.")
        return

    extensions = normalize_extensions(args.extensions)
    cleanup(
        target_dir,
        keep_days=max(args.days, 0),
        extensions=extensions,
        skip_tokens=args.skip_tokens,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
