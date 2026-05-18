import json
import os
import time
from pathlib import Path
from typing import Callable
import pandas as pd
import httpx
import requests
from tests.end_to_end_testing.llm_judge import judge

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
    """
    For every entry in a reference JSON file:
      - Send the question to the chatbot
      - Judge the response against the reference answer
      - Return accuracy and average response time
    """
    count_pass = 0
    count_partial = 0
    count_fail = 0
    total_time = 0
    total_errors = 0

    for case in reference_cases:
        print(f"\n[ID {case['id']}] Testing question: {case.get('question', 'N/A')}")
        # ── 1. Setup ───────────────────────────────────────────────────────
        start_res = client.post("/chat/start")
        if start_res.status_code != 200:
            print(f"  Failed to start chat session: {start_res.text}")
            total_errors += 1
            continue
        session_id = start_res.json()["session_id"]

        try:
            # ── 2. Act ─────────────────────────────────────────────────────
            start_time = time.time()
            response = client.post(
                "/chat/message",
                json={"session_id": session_id, "prompt": case["question"]},
                timeout=timeout_sec,  # ← add this
            )
            total_time += time.time() - start_time
            if response.status_code != 200:
                print(f"  Failed to get chat response: {response.text}")
                total_errors += 1
                continue
            actual_response: str = response.json()["response"]
            assert actual_response, f"[ID {case['id']}] Empty response from chatbot"

            # ── 3. Assert ──────────────────────────────────────────────────
            reference_answer = answer_to_human_string(case)
            verdict, reason = judge(
                question=case.get("question", "Unknown question"),
                reference_answer=reference_answer,
                actual_response=actual_response,
            )

            if verdict == "PASS":
                count_pass += 1
            elif verdict == "PARTIAL":
                count_partial += 1
                print(
                    f"\n[ID {case['id']}] {case['question']!r}"
                    f"\nVerdict : {verdict}"
                    f"\nReason  : {reason}"
                    f"\nReference:\n{reference_answer}"
                    f"\nActual:\n{actual_response[:400]}"
                )
            else:
                count_fail += 1
                print(
                    f"\n[ID {case['id']}] {case['question']!r}"
                    f"\nVerdict : {verdict}"
                    f"\nReason  : {reason}"
                    f"\nReference:\n{reference_answer}"
                    f"\nActual:\n{actual_response[:400]}"
                )
        except (TimeoutError, httpx.TimeoutException, requests.exceptions.Timeout):
            elapsed = time.time() - start_time
            print(f"  [ID {case['id']}] Timed out after {elapsed:.1f}s — skipping.")
            total_errors += 1
            continue
        finally:
            # ── 4. Teardown ────────────────────────────────────────────────
            client.post("/chat/end", json={"session_id": session_id})

    n = len(reference_cases)
    return {
        "count_pass": count_pass,
        "count_partial": count_partial,
        "count_fail": count_fail,
        "average_response_time_sec": total_time / n if n else 0,
        "total_errors": total_errors,
    }


def test_chat_response_wrapper(client):
    test_data_files = [f for f in os.listdir(TEST_DATA_DIR) if f.endswith(".json")]
    all_stats = pd.DataFrame(columns=["test_file", "accuracy", "average_response_time_sec"])
    for file in test_data_files:
        print(f"\n=== Running tests for {file} ===")
        test_data_path = os.path.join(TEST_DATA_DIR, file)
        reference_cases = load_reference_data(test_data_path)
        stats = chat_response_stats(client, reference_cases)
        all_stats = pd.concat([all_stats, pd.DataFrame([{
            "test_file": file,
            "count_pass": stats["count_pass"],
            "count_partial": stats["count_partial"],
            "count_fail": stats["count_fail"],
            "average_response_time_sec": stats["average_response_time_sec"],
            "total_errors": stats["total_errors"]
        }])], ignore_index=True)
        print(f"Stats for {file}: {stats}")
    results_dir = TEST_DIR / "results"
    results_dir.mkdir(exist_ok=True)
    all_stats.to_csv(results_dir / "chat_response_stats.csv", index=False)



