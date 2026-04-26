#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.RAG.databaseservice import DatabaseService  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a single schema_context.txt file for RAG prompts."
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=2,
        help="Number of sample rows per table.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db = DatabaseService()
    db.build_and_save_schema_context_file(sample_rows_per_table=args.samples)
    print(f"Schema context written to: {db.get_schema_context_file_path()}")


if __name__ == "__main__":
    main()
