from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SCRIPT_ORDER = [
    "ingest_excel.py",
    "build_schema_context.py",
    "build_metadata.py",
    "metadata_graph_to_dbml.py",
]


def main() -> int:
    scripts_dir = Path(__file__).resolve().parent

    missing = [name for name in SCRIPT_ORDER if not (scripts_dir / name).exists()]
    if missing:
        print("Missing required setup scripts in 'scripts' folder:")
        for name in missing:
            print(f" - {name}")
        print("\nPlace all required scripts in the 'scripts' folder, then run again.")
        return 1

    for name in SCRIPT_ORDER:
        script_path = scripts_dir / name
        print(f"\n>>> Running {name}")
        result = subprocess.run([sys.executable, str(script_path)], cwd=scripts_dir.parent)
        if result.returncode != 0:
            print(f"\nSetup failed while running {name} (exit code {result.returncode}).")
            return result.returncode

    print("\nSetup completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
