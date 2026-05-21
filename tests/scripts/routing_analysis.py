"""
scripts/analyze_routing.py

Extracts expected vs. actual handler routing from test run logs
and prints a confusion summary.

Usage:
    python scripts/analyze_routing.py logs/test_run_20260520_112723.log
"""

import re
import sys
from collections import defaultdict
from pathlib import Path
import os

CURRENT_DIR = Path(__file__).resolve().parent
TESTS_DIR = CURRENT_DIR.parent
ROOT_DIR = TESTS_DIR.parent


# Maps test file name → expected handler for all its IDs
EXPECTED_HANDLER = {
    "reference_answers_data_handler.json":          "data_handler",
    "reference_answers_conversational_handler.json": "conversational_handler",
    "reference_answers_metadata_handler.json":       "metadata_handler",
    "reference_answers_web_handler.json":            "web_handler",
}


def parse_log(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    records = []
    current_suite = None

    for line in text.splitlines():
        # Track which test suite we're in
        m = re.search(r"Running tests for (.+\.json)", line)
        if m:
            current_suite = m.group(1)

        # Track test ID + prompt
        m = re.match(r"\[ID (\d+)\] Testing: (.+)", line.strip())
        if m and current_suite:
            records.append({
                "suite":    current_suite,
                "id":       int(m.group(1)),
                "prompt":   m.group(2).strip(),
                "expected": EXPECTED_HANDLER.get(current_suite, "unknown"),
                "actual":   None,
            })

        # Capture the intent determined for the most recent record
        m = re.match(r"Determined intent: (.+)", line.strip())
        if m and records and records[-1]["actual"] is None:
            records[-1]["actual"] = m.group(1).strip().lower()

    return [r for r in records if r["actual"]]


def print_confusion(records: list[dict]) -> None:
    # confusion[expected][actual] = count
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    mistakes: list[dict] = []

    for r in records:
        confusion[r["expected"]][r["actual"]] += 1
        if r["expected"] != r["actual"]:
            mistakes.append(r)

    all_handlers = sorted({r["expected"] for r in records} | {r["actual"] for r in records})

    # --- Confusion matrix ---
    col_w = 26
    print("\n=== Routing Confusion Matrix (rows=expected, cols=actual) ===\n")
    header = f"{'':26}" + "".join(f"{h[:col_w]:>{col_w}}" for h in all_handlers)
    print(header)
    print("-" * len(header))
    for expected in all_handlers:
        row = f"{expected:26}"
        for actual in all_handlers:
            count = confusion[expected].get(actual, 0)
            cell = str(count) if count else "."
            row += f"{cell:>{col_w}}"
        print(row)

    # --- Mistake pairs summary ---
    pair_counts: dict[tuple, int] = defaultdict(int)
    for m in mistakes:
        pair_counts[(m["expected"], m["actual"])] += 1

    print(f"\n=== Misrouting Summary ({len(mistakes)} mistakes / {len(records)} total) ===\n")
    print(f"  {'Expected':<30} {'Got':<30} {'Count':>5}")
    print("  " + "-" * 68)
    for (exp, act), count in sorted(pair_counts.items(), key=lambda x: -x[1]):
        print(f"  {exp:<30} {act:<30} {count:>5}")

    # --- Example prompts per mistake pair ---
    print("\n=== Example Misrouted Prompts ===\n")
    shown: dict[tuple, int] = defaultdict(int)
    for m in mistakes:
        key = (m["expected"], m["actual"])
        if shown[key] < 3:
            print(f"  [{m['expected']} → {m['actual']}] {m['prompt'][:90]}")
            shown[key] += 1


if __name__ == "__main__":
    logs_dir = ROOT_DIR / "tests" / "logs"
    if len(sys.argv) > 1:
        log_path = Path(sys.argv[1])
    else:
        log_files = list(logs_dir.glob("*.log"))

        if log_files:
            log_path = max(log_files, key=lambda p: p.stat().st_mtime)
        else:
            log_path = None
            print(f"Warning: No log files found in {logs_dir}")
            sys.exit(1)

    records = parse_log(log_path)
    print(f"Parsed {len(records)} routing decisions from {log_path.name}")
    print_confusion(records)
