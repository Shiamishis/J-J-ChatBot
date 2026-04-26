#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Based on NovaCarta EMEA data model overview + logical model HTML
TABLE_ROLES = {
    "DIM_Geography": "dimension",
    "DIM_Brand": "dimension",
    "DIM_Brand_Indication": "bridge",
    "DIM_Time": "dimension",
    "DIM_Employee": "dimension",
    "DIM_Account": "dimension",
    "FACT_Interactions": "fact",
    "FACT_Coverage": "fact",
    "FACT_Performance": "fact",
    "FACT_Sales": "fact",
    "FACT_Account_Metrics": "fact",
    "FACT_KPI_Summary": "fact",
    "FACT_Sample_Management": "fact",
    "FACT_Targets": "fact",
}

PRIMARY_KEYS = {
    "DIM_Geography": "geo_id",
    "DIM_Brand": "brand_id",
    "DIM_Brand_Indication": "indication_id",
    "DIM_Time": "time_id",
    "DIM_Employee": "employee_id",
    "DIM_Account": "account_id",
    "FACT_Interactions": "interaction_id",
    "FACT_Coverage": "coverage_id",
    "FACT_Performance": "performance_id",
    "FACT_Sales": "sales_id",
    "FACT_Account_Metrics": "account_metric_id",
    "FACT_KPI_Summary": "kpi_summary_id",
    "FACT_Sample_Management": "sample_id",
    "FACT_Targets": "target_id",
}

# (source_table, source_column, target_table, target_column, relation_type, confidence)
EDGES = [
    # FACT_Interactions
    ("FACT_Interactions", "account_id", "DIM_Account", "account_id", "documented_fk", 1.0),
    ("FACT_Interactions", "employee_id", "DIM_Employee", "employee_id", "documented_fk", 1.0),
    ("FACT_Interactions", "brand_id", "DIM_Brand", "brand_id", "documented_fk", 1.0),
    ("FACT_Interactions", "indication_id", "DIM_Brand_Indication", "indication_id", "documented_fk", 1.0),
    ("FACT_Interactions", "geo_id", "DIM_Geography", "geo_id", "documented_fk", 1.0),
    ("FACT_Interactions", "time_id", "DIM_Time", "time_id", "documented_fk", 1.0),

    # FACT_Sales
    ("FACT_Sales", "account_id", "DIM_Account", "account_id", "documented_fk", 1.0),
    ("FACT_Sales", "geo_id", "DIM_Geography", "geo_id", "documented_fk", 1.0),
    ("FACT_Sales", "brand_id", "DIM_Brand", "brand_id", "documented_fk", 1.0),
    ("FACT_Sales", "time_id", "DIM_Time", "time_id", "documented_fk", 1.0),

    # FACT_Coverage
    ("FACT_Coverage", "geo_id", "DIM_Geography", "geo_id", "documented_fk", 1.0),
    ("FACT_Coverage", "brand_id", "DIM_Brand", "brand_id", "documented_fk", 1.0),
    ("FACT_Coverage", "time_id", "DIM_Time", "time_id", "documented_fk", 1.0),

    # FACT_Performance
    ("FACT_Performance", "employee_id", "DIM_Employee", "employee_id", "documented_fk", 1.0),
    ("FACT_Performance", "geo_id", "DIM_Geography", "geo_id", "documented_fk", 1.0),
    ("FACT_Performance", "brand_id", "DIM_Brand", "brand_id", "documented_fk", 1.0),
    ("FACT_Performance", "time_id", "DIM_Time", "time_id", "documented_fk", 1.0),

    # FACT_Account_Metrics
    ("FACT_Account_Metrics", "account_id", "DIM_Account", "account_id", "documented_fk", 1.0),
    ("FACT_Account_Metrics", "brand_id", "DIM_Brand", "brand_id", "documented_fk", 1.0),
    ("FACT_Account_Metrics", "territory_id", "DIM_Geography", "geo_id", "documented_fk", 1.0),
    ("FACT_Account_Metrics", "time_id", "DIM_Time", "time_id", "documented_fk", 1.0),

    # FACT_KPI_Summary
    ("FACT_KPI_Summary", "geo_id", "DIM_Geography", "geo_id", "documented_fk", 1.0),
    ("FACT_KPI_Summary", "brand_id", "DIM_Brand", "brand_id", "documented_fk", 1.0),
    ("FACT_KPI_Summary", "time_id", "DIM_Time", "time_id", "documented_fk", 1.0),

    # FACT_Sample_Management
    ("FACT_Sample_Management", "interaction_id", "FACT_Interactions", "interaction_id", "documented_fk", 1.0),
    ("FACT_Sample_Management", "account_id", "DIM_Account", "account_id", "documented_fk", 1.0),
    ("FACT_Sample_Management", "employee_id", "DIM_Employee", "employee_id", "documented_fk", 1.0),
    ("FACT_Sample_Management", "brand_id", "DIM_Brand", "brand_id", "documented_fk", 1.0),
    ("FACT_Sample_Management", "time_id", "DIM_Time", "time_id", "documented_fk", 1.0),

    # FACT_Targets
    ("FACT_Targets", "geo_id", "DIM_Geography", "geo_id", "documented_fk", 1.0),
    ("FACT_Targets", "brand_id", "DIM_Brand", "brand_id", "documented_fk", 1.0),
    ("FACT_Targets", "time_id", "DIM_Time", "time_id", "documented_fk", 1.0),

    # DIM->DIM / hierarchy
    ("DIM_Brand_Indication", "brand_id", "DIM_Brand", "brand_id", "documented_fk", 1.0),
    ("DIM_Employee", "territory_id", "DIM_Geography", "geo_id", "documented_fk", 1.0),
    ("DIM_Account", "territory_id", "DIM_Geography", "geo_id", "documented_fk", 1.0),

    # optional self-hierarchies from logical model
    ("DIM_Geography", "parent_geo_id", "DIM_Geography", "geo_id", "documented_self_fk", 0.95),
    ("DIM_Employee", "manager_id", "DIM_Employee", "employee_id", "documented_self_fk", 0.95),
]

def existing_tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
    """).fetchall()
    return {r[0] for r in rows}

def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
    return {r[1] for r in rows}

def create_metadata_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS _metadata_tables (
        table_name TEXT PRIMARY KEY,
        table_role TEXT,
        row_count INTEGER NOT NULL DEFAULT 0,
        column_count INTEGER NOT NULL DEFAULT 0,
        primary_key_column TEXT
    );

    CREATE TABLE IF NOT EXISTS _metadata_columns (
        table_name TEXT NOT NULL,
        column_name TEXT NOT NULL,
        sqlite_type TEXT,
        is_pk INTEGER NOT NULL DEFAULT 0,
        is_not_null INTEGER NOT NULL DEFAULT 0,
        ordinal_position INTEGER NOT NULL,
        PRIMARY KEY (table_name, column_name)
    );

    CREATE TABLE IF NOT EXISTS _metadata_foreign_keys (
        source_table TEXT NOT NULL,
        source_column TEXT NOT NULL,
        target_table TEXT NOT NULL,
        target_column TEXT NOT NULL,
        relation_type TEXT NOT NULL,
        confidence REAL NOT NULL,
        PRIMARY KEY (source_table, source_column, target_table, target_column)
    );

    CREATE TABLE IF NOT EXISTS _metadata_semantic_columns (
        table_name TEXT NOT NULL,
        column_name TEXT NOT NULL,
        semantic_role TEXT NOT NULL, -- metric | dimension_attr | time | id | flag
        PRIMARY KEY (table_name, column_name, semantic_role)
    );
    """)

def semantic_role(column: str) -> str:
    c = column.lower()
    if c.endswith("_id") or c == "id":
        return "id"
    if "time" in c or c in {"year", "quarter", "month", "fiscal_year", "fiscal_quarter", "year_month"}:
        return "time"
    if c.startswith("is_") or c.endswith("_flag"):
        return "flag"
    if c.endswith("_pct") or "revenue" in c or "units" in c or "count" in c or "value" in c or "score" in c or "volume" in c:
        return "metric"
    return "dimension_attr"

def rebuild_metadata(conn: sqlite3.Connection) -> dict:
    create_metadata_schema(conn)

    conn.execute("DELETE FROM _metadata_tables")
    conn.execute("DELETE FROM _metadata_columns")
    conn.execute("DELETE FROM _metadata_foreign_keys")
    conn.execute("DELETE FROM _metadata_semantic_columns")

    tables_in_db = existing_tables(conn)
    managed_tables = sorted([t for t in TABLE_ROLES if t in tables_in_db])

    for table in managed_tables:
        cols_info = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
        row_count = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        pk_col = PRIMARY_KEYS.get(table)

        conn.execute("""
            INSERT INTO _metadata_tables(table_name, table_role, row_count, column_count, primary_key_column)
            VALUES (?, ?, ?, ?, ?)
        """, (table, TABLE_ROLES.get(table), row_count, len(cols_info), pk_col))

        for col in cols_info:
            cid, name, col_type, notnull, _default, _pk_flag = col
            is_pk = 1 if name == pk_col else 0
            conn.execute("""
                INSERT INTO _metadata_columns(table_name, column_name, sqlite_type, is_pk, is_not_null, ordinal_position)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (table, name, col_type or "", is_pk, int(bool(notnull)), cid))
            conn.execute("""
                INSERT INTO _metadata_semantic_columns(table_name, column_name, semantic_role)
                VALUES (?, ?, ?)
            """, (table, name, semantic_role(name)))

    inserted_edges = 0
    skipped_edges = []
    for s_table, s_col, t_table, t_col, rel_type, conf in EDGES:
        if s_table not in tables_in_db or t_table not in tables_in_db:
            skipped_edges.append((s_table, s_col, t_table, t_col, "table_missing"))
            continue
        s_cols = table_columns(conn, s_table)
        t_cols = table_columns(conn, t_table)
        if s_col not in s_cols or t_col not in t_cols:
            skipped_edges.append((s_table, s_col, t_table, t_col, "column_missing"))
            continue

        conn.execute("""
            INSERT OR REPLACE INTO _metadata_foreign_keys(
                source_table, source_column, target_table, target_column, relation_type, confidence
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (s_table, s_col, t_table, t_col, rel_type, conf))
        inserted_edges += 1

    conn.commit()

    return {
        "managed_tables": managed_tables,
        "inserted_edges": inserted_edges,
        "skipped_edges": skipped_edges,
    }

def export_json(conn: sqlite3.Connection, path: Path) -> None:
    nodes = [r[0] for r in conn.execute(
        "SELECT table_name FROM _metadata_tables ORDER BY table_name"
    ).fetchall()]
    edges = conn.execute("""
        SELECT source_table, source_column, target_table, target_column, relation_type, confidence
        FROM _metadata_foreign_keys
        ORDER BY source_table, source_column, target_table
    """).fetchall()

    payload = {
        "nodes": nodes,
        "edges": [
            {
                "source_table": r[0],
                "source_column": r[1],
                "target_table": r[2],
                "target_column": r[3],
                "relation_type": r[4],
                "confidence": r[5],
            }
            for r in edges
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

def main() -> None:
    parser = argparse.ArgumentParser(description="Manual metadata + graph edge bootstrap for NovaCarta SQLite DB.")
    parser.add_argument("--db", default=str(ROOT / "local.db"), help="Path to SQLite DB")
    parser.add_argument("--out", default=str(ROOT / "data" / "metadata_graph_manual.json"), help="Output graph JSON")
    args = parser.parse_args()

    db_path = Path(args.db).resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")

    with sqlite3.connect(str(db_path)) as conn:
        summary = rebuild_metadata(conn)
        export_json(conn, Path(args.out).resolve())

    print(f"Metadata built for {len(summary['managed_tables'])} managed tables")
    print(f"Inserted edges: {summary['inserted_edges']}")
    print(f"Skipped edges: {len(summary['skipped_edges'])}")
    if summary["skipped_edges"]:
        print("First skipped edge examples:")
        for item in summary["skipped_edges"][:10]:
            print("  ", item)

if __name__ == "__main__":
    main()