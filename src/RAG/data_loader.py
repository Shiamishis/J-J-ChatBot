# This file is not used currently
import json
import re
from pathlib import Path
from typing import Optional, List
import docx  # New import


class ReferenceDataLoader:
    """
    Handles loading, cleaning, and truncating reference metadata files.
    Supports: .html, .json, .docx, .md, .txt
    """

    def __init__(
            self,
            data_dir: str = "data",
            max_chars_per_file: int = 12000,
            max_total_chars: int = 30000,
            allowed_extensions: Optional[List[str]] = None
    ):
        self.data_dir = Path(data_dir)
        self.max_chars_per_file = max_chars_per_file
        self.max_total_chars = max_total_chars
        # Added .docx to the default list
        self.allowed_extensions = allowed_extensions or [".html", ".json", ".docx", ".md", ".txt", ".csv", ".dbml"]

    @staticmethod
    def strip_html(raw_html: str) -> str:
        no_script = re.sub(r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>", " ", raw_html, flags=re.IGNORECASE)
        no_style = re.sub(r"<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>", " ", no_script, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", no_style)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _read_docx(self, path: Path) -> str:
        """Extracts text from paragraphs in a .docx file."""
        try:
            doc = docx.Document(path)
            full_text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text)
            return "\n".join(full_text)
        except Exception as e:
            return f"Error reading docx: {e}"

    def load_data(self, specific_files: Optional[List[str]] = None) -> str:
        if not self.data_dir.exists():
            return f"Data directory not found: {self.data_dir}"

        if specific_files:
            file_paths = [self.data_dir / f for f in specific_files]
        else:
            file_paths = sorted([
                f for f in self.data_dir.iterdir()
                if f.is_file() and f.suffix.lower() in self.allowed_extensions
            ])

        sections: list[str] = []
        used_chars = 0

        for path in file_paths:
            if not path.exists():
                continue
            if used_chars >= self.max_total_chars:
                break

            try:
                content = self._process_file(path)
                content = content[:self.max_chars_per_file]

                block = f"[{path.name}]\n{content}"

                if used_chars + len(block) > self.max_total_chars:
                    remaining = self.max_total_chars - used_chars
                    if remaining > 0:
                        sections.append(block[:remaining])
                    break

                sections.append(block)
                used_chars += len(block)

            except Exception as e:
                sections.append(f"[{path.name}] load_error={e}")

        return "\n\n".join(sections) if sections else "No relevant metadata files found."

    def _process_file(self, path: Path) -> str:
        ext = path.suffix.lower()

        # Docx is binary, so we handle it before the general read_text
        if ext == ".docx":
            return self._read_docx(path)

        # Other formats are text-based
        raw = path.read_text(encoding="utf-8", errors="ignore")

        if ext == ".html":
            return self.strip_html(raw)
        if ext == ".json":
            try:
                parsed = json.loads(raw)
                return json.dumps(parsed, ensure_ascii=True, separators=(",", ":"))
            except json.JSONDecodeError:
                return raw
        return raw