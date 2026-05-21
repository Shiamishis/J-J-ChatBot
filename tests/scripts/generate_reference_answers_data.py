import json
import sqlite3
from pathlib import Path

import pandas as pd


# =========================
# PATH SETUP
# =========================

# tests/
CURRENT_DIR = Path(__file__).resolve().parent
TEST_DIR = CURRENT_DIR.parent
# project root/
PROJECT_ROOT = CURRENT_DIR.parent.parent

# files
INPUT_FILE = TEST_DIR / "supplementary_data" / "questions_sql.json"
OUTPUT_FILE = TEST_DIR / "test_data" / "reference_answers_data_handler.json"

# database
DATABASE_PATH = PROJECT_ROOT / "local.db"


# =========================
# HELPERS
# =========================

def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize dataframe ordering for stable comparisons.
    """

    # sort columns alphabetically
    df = df.sort_index(axis=1)

    # sort rows
    if len(df.columns) > 0:
        df = df.sort_values(by=list(df.columns)).reset_index(drop=True)

    return df


def dataframe_to_serializable(df: pd.DataFrame) -> dict:
    """
    Convert DataFrame into JSON serializable structure.
    """

    return {
        "columns": list(df.columns),
        "rows": df.values.tolist()
    }


# =========================
# MAIN LOGIC
# =========================

def main():

    print(f"Reading benchmark questions from:\n{INPUT_FILE}\n")

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        benchmark_data = json.load(f)

    conn = sqlite3.connect(DATABASE_PATH)

    reference_dataset = []

    for item in benchmark_data:

        question_id = item["id"]
        question = item["question"]
        sql = item["sql"]

        print(f"Processing [{question_id}] {question}")

        try:

            # execute SQL
            df = pd.read_sql_query(sql, conn)

            # normalize for stable comparisons
            df = normalize_dataframe(df)

            # convert to JSON format
            answer = dataframe_to_serializable(df)

            reference_dataset.append({
                "id": question_id,
                "question": question,
                "sql": sql,
                "answer": answer
            })

            print("SUCCESS\n")

        except Exception as e:

            reference_dataset.append({
                "id": question_id,
                "question": question,
                "sql": sql,
                "error": str(e)
            })

            print(f"FAILED: {e}\n")

    conn.close()

    # save generated dataset
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(reference_dataset, f, indent=4)

    print("=" * 50)
    print("Reference answers generated successfully.")
    print(f"Saved to:\n{OUTPUT_FILE}")
    print("=" * 50)


if __name__ == "__main__":
    main()