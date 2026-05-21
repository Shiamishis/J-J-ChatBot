import json
import os
import time
from pathlib import Path
from typing import Callable
import pandas as pd
import httpx
import requests
from tests.end_to_end_testing.llm_judge import judge
import datetime
import sys

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------

class LoggerTee:
    """
    A simple class to write to both a file and the standard console output.
    This captures everything printed via sys.stdout.
    """

    def __init__(self, log_file):
        self.terminal = sys.stdout
        self.log = open(log_file, "a", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        # Flush ensures logs are written in real-time if the script crashes
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()


def setup_logging():
    """Sets up the logs directory and redirects stdout to a file."""
    # Using your existing TEST_DIR logic
    log_dir = TEST_DIR / "logs"
    log_dir.mkdir(exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = log_dir / f"test_run_{timestamp}.log"

    print(f"--- Logging to: {log_filename} ---")

    # Redirect stdout and stderr to the log file
    sys.stdout = LoggerTee(log_filename)
    sys.stderr = LoggerTee(log_filename)

    return log_filename

# ---------------------------------------------------------------------------
# Reference data loader
# ---------------------------------------------------------------------------
CURRENT_DIR = Path(__file__).resolve().parent
TEST_DIR = CURRENT_DIR.parent
TEST_DATA_DIR = os.path.join(TEST_DIR, "test_data")


def load_reference_data(test_data_path) -> list[dict]:
    with open(test_data_path, "r") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Answer format handler registry
#
# Each handler is a dict with two keys:
#   "detect"  : Callable[[dict], bool]   — returns True if this handler owns
#                                          the given `answer` value
#   "render"  : Callable[[str, dict], str] — converts (question, answer) into
#                                            a human-readable reference string
#
# Handlers are tried in registration order; the first match wins.
# To support a new answer format, append a new entry to ANSWER_HANDLERS —
# no other code needs to change.
# ---------------------------------------------------------------------------

def _fmt_value(value: float | int | str) -> str:
    """Format a single cell value for human readability."""
    if isinstance(value, str):
        return value
    if isinstance(value, float):
        value = round(value, 2)
    if isinstance(value, (int, float)) and value >= 1_000:
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    return str(value)


# ── Handler: tabular SQL result  {"columns": [...], "rows": [[...], ...]} ──

def _detect_tabular(answer) -> bool:
    return (
        isinstance(answer, dict)
        and "columns" in answer
        and "rows" in answer
    )


def _render_tabular(question: str, answer: dict) -> str:
    columns: list[str] = answer.get("columns", [])
    rows: list[list] = answer.get("rows", [])

    if not rows:
        return f'For the question "{question}", no data was returned.'

    n_cols = len(columns)
    lines: list[str] = [f'For the question "{question}", the expected answer is:']

    if n_cols == 1:
        label = columns[0] if columns else "value"
        items = ", ".join(_fmt_value(r[0]) for r in rows)
        lines.append(f"  {label}: {items}")

    elif n_cols == 2:
        for row in rows:
            lines.append(f"  - {_fmt_value(row[0])}: {_fmt_value(row[1])}")

    else:
        for row in rows:
            parts = [f"{col} = {_fmt_value(val)}" for col, val in zip(columns, row)]
            lines.append("  - " + ", ".join(parts))

    return "\n".join(lines)


# ── Handler: plain string answer  {"answer": "some text ..."}  ─────────────

def _detect_plain_string(answer) -> bool:
    return isinstance(answer, str)


def _render_plain_string(question: str, answer: str) -> str:
    return (
        f'For the question "{question}", the expected answer is:\n'
        f"  {answer}"
    )


# ── Registry (extend here) ──────────────────────────────────────────────────

ANSWER_HANDLERS: list[dict[str, Callable]] = [
    {"detect": _detect_tabular,      "render": _render_tabular},
    {"detect": _detect_plain_string, "render": _render_plain_string},
    # Add new handlers here, e.g.:
    # {"detect": _detect_my_format, "render": _render_my_format},
]


# ---------------------------------------------------------------------------
# Public entry point (replaces the old answer_to_human_string)
# ---------------------------------------------------------------------------

def answer_to_human_string(case: dict) -> str:
    """
    Dispatch to the correct answer renderer based on the structure of
    case["answer"], using the ANSWER_HANDLERS registry.
    """
    question: str = case.get("question", "Unknown question")
    answer = case.get("answer")

    if answer is None:
        return f'For the question "{question}", no answer was provided.'

    for handler in ANSWER_HANDLERS:
        if handler["detect"](answer):
            return handler["render"](question, answer)

    # Fallback: no registered handler matched
    return (
        f'For the question "{question}", the expected answer is:\n'
        f"  {answer!r}"
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def chat_response_stats(client, reference_cases, timeout_sec=30):
    count_pass = 0
    count_partial = 0
    count_fail = 0
    total_time = 0
    total_errors = 0

    for case in reference_cases:
        print(f"\n[ID {case['id']}] Testing: {case.get('question') or case.get('turns', [{}])[-1].get('prompt', 'N/A')}")

        start_res = client.post("/chat/start")
        if start_res.status_code != 200:
            print(f"  Failed to start chat session: {start_res.text}")
            total_errors += 1
            continue

        session_id = start_res.json()["session_id"]

        try:
            # ── Normalise: single-turn cases get wrapped into turns format ─
            turns = case.get("turns") or [
                {"prompt": case["question"], "answer": case["answer"]}
            ]

            actual_response = None
            start_time = time.time()

            for i, turn in enumerate(turns):
                is_last = i == len(turns) - 1
                response = client.post(
                    "/chat/message",
                    json={"session_id": session_id, "prompt": turn["prompt"]},
                    timeout=timeout_sec,
                )
                if response.status_code != 200:
                    print(f"  Failed on turn {i+1}: {response.text}")
                    total_errors += 1
                    break
                actual_response = response.json()["response"]
                assert actual_response, f"[ID {case['id']}] Empty response on turn {i+1}"

                # Only judge intermediate turns if they have an expected answer
                if not is_last and "answer" in turn:
                    ref = answer_to_human_string({"question": turn["prompt"], "answer": turn["answer"]})
                    verdict, reason = judge(
                        question=turn["prompt"],
                        reference_answer=ref,
                        actual_response=actual_response,
                    )
                    if verdict == "FAIL":
                        print(f"  [ID {case['id']}] Turn {i+1} failed, aborting sequence.\n  Reason: {reason}")
                        total_errors += 1
                        actual_response = None
                        break

            total_time += time.time() - start_time

            if actual_response is None:
                continue

            # ── Judge only the final turn ──────────────────────────────────
            final_turn = turns[-1]
            reference_answer = answer_to_human_string({
                "question": final_turn["prompt"],
                "answer": final_turn["answer"]
            })
            verdict, reason = judge(
                question=final_turn["prompt"],
                reference_answer=reference_answer,
                actual_response=actual_response,
            )

            if verdict == "PASS":
                count_pass += 1
            elif verdict == "PARTIAL":
                count_partial += 1
                print(f"\n[ID {case['id']}] Verdict: {verdict}\nReason: {reason}")
            else:
                count_fail += 1
                print(
                    f"\n[ID {case['id']}] Verdict: {verdict}"
                    f"\nReference: {reference_answer}"
                    f"\nActual: {actual_response[:400]}"
                    f"\nReason: {reason}"
                )

        except (TimeoutError, httpx.TimeoutException, requests.exceptions.Timeout):
            elapsed = time.time() - start_time
            print(f"  [ID {case['id']}] Timed out after {elapsed:.1f}s — skipping.")
            total_errors += 1
            continue
        except AssertionError as e:
            print(f"  [ID {case['id']}] Assertion error: {e}")
            total_errors += 1
            continue
        finally:
            client.post("/chat/end", json={"session_id": session_id})

    n = len(reference_cases)
    return {
        "ratio_pass": count_pass / n if n else 0,
        "ratio_partial": count_partial / n if n else 0,
        "ratio_fail": count_fail / n if n else 0,
        "average_response_time_sec": total_time / n if n else 0,
        "ratio_errors": total_errors / n if n else 0,
    }

def test_chat_response_wrapper(client):
    log_file_path = setup_logging()
    test_data_files = [f for f in os.listdir(TEST_DATA_DIR) if f.endswith(".json")]
    all_stats = pd.DataFrame(columns=["test_file", "accuracy", "average_response_time_sec"])
    for file in test_data_files:
        print(f"\n=== Running tests for {file} ===")
        test_data_path = os.path.join(TEST_DATA_DIR, file)
        reference_cases = load_reference_data(test_data_path)
        stats = chat_response_stats(client, reference_cases)
        all_stats = pd.concat([all_stats, pd.DataFrame([{
            "test_file": file,
            "ratio_pass": stats["ratio_pass"],
            "ratio_partial": stats["ratio_partial"],
            "ratio_fail": stats["ratio_fail"],
            "average_response_time_sec": stats["average_response_time_sec"],
            "ratio_errors": stats["ratio_errors"]
        }])], ignore_index=True)
        print(f"Stats for {file}: {stats}")
    results_dir = TEST_DIR / "results"
    results_dir.mkdir(exist_ok=True)
    all_stats.to_csv(results_dir / "chat_response_stats.csv", index=False)



