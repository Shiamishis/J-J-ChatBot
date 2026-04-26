#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def infer_table_kind(table_name: str) -> str:
    if table_name.startswith("DIM_"):
        return "dimension"
    if table_name.startswith("FACT_"):
        return "fact"
    if "bridge" in table_name.lower():
        return "bridge"
    return "table"


def build_dbml(metadata_graph: dict) -> str:
    nodes = sorted(set(metadata_graph.get("nodes", [])))
    edges = metadata_graph.get("edges", [])

    table_columns: dict[str, set[str]] = defaultdict(set)
    inbound_counts: dict[tuple[str, str], int] = defaultdict(int)

    for edge in edges:
        src_table = edge["source_table"]
        src_col = edge["source_column"]
        dst_table = edge["target_table"]
        dst_col = edge["target_column"]

        table_columns[src_table].add(src_col)
        table_columns[dst_table].add(dst_col)
        inbound_counts[(dst_table, dst_col)] += 1

    # Ensure every listed node gets emitted even if it has no columns from edges.
    for node in nodes:
        table_columns.setdefault(node, set())

    lines: list[str] = []
    lines.append("// Generated from metadata_graph_manual.json")
    lines.append("// Format: DBML (https://dbml.dbdiagram.io/)")
    lines.append("")

    for table_name in nodes:
        kind = infer_table_kind(table_name)
        lines.append(f'Table "{table_name}" {{')

        cols = sorted(table_columns[table_name])
        if not cols:
            lines.append('  placeholder_id text [note: "No columns available in source graph"]')
        else:
            for col in cols:
                is_pk = inbound_counts[(table_name, col)] > 0 and col.endswith("_id")
                if is_pk:
                    lines.append(f"  {col} text [pk]")
                else:
                    lines.append(f"  {col} text")

        lines.append(f'  Note: "{kind}"')
        lines.append("}")
        lines.append("")

    lines.append("// Foreign-key style relationships")
    for edge in edges:
        src_table = edge["source_table"]
        src_col = edge["source_column"]
        dst_table = edge["target_table"]
        dst_col = edge["target_column"]
        rel_type = edge.get("relation_type", "fk")
        confidence = edge.get("confidence", 1.0)
        lines.append(
            f'Ref: "{src_table}"."{src_col}" > "{dst_table}"."{dst_col}" '
            f'// {rel_type}, confidence={confidence}'
        )

    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert metadata graph JSON to DBML for LLM-friendly schema consumption."
    )
    parser.add_argument(
        "--input",
        default="data/metadata_graph_manual.json",
        help="Path to metadata graph JSON input.",
    )
    parser.add_argument(
        "--output",
        default="data/metadata_graph_manual.dbml",
        help="Path for generated DBML output.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    dbml_text = build_dbml(payload)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(dbml_text, encoding="utf-8")
    print(f"DBML written to: {output_path}")


if __name__ == "__main__":
    main()
