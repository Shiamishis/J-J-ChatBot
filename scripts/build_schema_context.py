#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Optional

from docx import Document


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Kept consistent with the original script structure so the script
    can be extended easily in the future.
    """
    parser = argparse.ArgumentParser(
        description="Parse technical documentation and save it as a text file."
    )

    parser.add_argument(
        "--output-name",
        type=str,
        default="documentation.txt",
        help="Name of the generated output file inside PROJECT_ROOT/data.",
    )

    return parser.parse_args()


def find_technical_documentation_file(data_dir: Path) -> Path:
    """
    Scan PROJECT_ROOT/data for a file containing
    'technical_documentation' in its filename.

    Returns:
        Path to the matched file.

    Raises:
        FileNotFoundError: If no matching file is found.
    """
    matching_files = [
        file_path
        for file_path in data_dir.iterdir()
        if file_path.is_file()
        and "technical_documentation" in file_path.stem.lower()
    ]

    if not matching_files:
        raise FileNotFoundError(
            "No file containing 'technical_documentation' was found in the data directory."
        )

    # Return the first match
    return matching_files[0]


def parse_documentation_file(file_path: Path) -> str:
    """
    Parse a documentation file into a plain text string.

    The parser is intentionally format-agnostic and uses the file
    extension to determine the parsing strategy.

    Supported:
    - .txt
    - .md
    - .docx

    Raises:
        ValueError: If the file format is unsupported.
    """
    suffix = file_path.suffix.lower()

    if suffix in {".txt", ".md"}:
        return file_path.read_text(encoding="utf-8")

    if suffix == ".docx":
        document = Document(file_path)
        paragraphs = [paragraph.text for paragraph in document.paragraphs]
        return "\n".join(paragraphs)

    raise ValueError(
        f"Unsupported documentation format: '{suffix}'. "
        "Supported formats are: .txt, .md, .docx"
    )


def save_documentation_text(
    documentation_text: str,
    output_path: Path,
) -> None:
    """
    Save parsed documentation text to disk.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        documentation_text,
        encoding="utf-8",
    )


def main() -> None:
    """
    Orchestrates the full pipeline:

    1. Scan PROJECT_ROOT/data for technical documentation.
    2. Parse the documentation into a string.
    3. Save the parsed text into PROJECT_ROOT/data/documentation.txt.
    """
    args = parse_args()

    data_dir = ROOT / "data"

    documentation_file = find_technical_documentation_file(data_dir)

    documentation_text = parse_documentation_file(documentation_file)

    output_path = data_dir / args.output_name

    save_documentation_text(
        documentation_text=documentation_text,
        output_path=output_path,
    )

    print(f"Documentation parsed from: {documentation_file}")
    print(f"Text file written to: {output_path}")


if __name__ == "__main__":
    main()