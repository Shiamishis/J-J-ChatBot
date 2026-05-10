#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Documentation parsing
# ---------------------------------------------------------------------------

# Table indices inside the Word document (0-based).
# Table 1  → Section 1.1 inventory  (Table | Type | Primary Key | Records | Description)
# Table 16 → Section 3 relationships (From Table | From Col | To Table | To Col | ...)
_INVENTORY_TABLE_INDEX = 1
_RELATIONSHIPS_TABLE_INDEX = 16


def get_table_roles(documentation_file: Path) -> dict[str, str]:
    """
    Parse the Section 1.1 inventory table and return:
        {table_name: role}   where role ∈ {"dimension", "fact", "bridge"}

    A row whose Description contains "bridge" is classified as "bridge"
    regardless of what the Type column says (catches DIM_Brand_Indication).
    """
    doc = Document(str(documentation_file))
    table = doc.tables[_INVENTORY_TABLE_INDEX]
    rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]

    header = [col.lower() for col in rows[0]]
    col_table = header.index("table")
    col_type  = header.index("type")
    col_desc  = header.index("description")

    roles: dict[str, str] = {}
    for row in rows[1:]:
        name = row[col_table]
        if not name:
            continue
        if "bridge" in row[col_desc].lower():
            roles[name] = "bridge"
        elif row[col_type].lower().startswith("fact"):
            roles[name] = "fact"
        else:
            roles[name] = "dimension"

    return roles


def get_primary_keys(documentation_file: Path) -> dict[str, str]:
    """
    Parse the Section 1.1 inventory table and return:
        {table_name: pk_column}

    For composite PKs (e.g. "brand_id + indication_id") only the *last*
    component is returned, matching the convention used in rebuild_metadata
    where a single primary_key_column string is stored.
    """
    doc = Document(str(documentation_file))
    table = doc.tables[_INVENTORY_TABLE_INDEX]
    rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]

    header = [col.lower() for col in rows[0]]
    col_table = header.index("table")
    col_pk    = header.index("primary key")

    pks: dict[str, str] = {}
    for row in rows[1:]:
        name = row[col_table]
        if not name:
            continue
        pk_raw = row[col_pk]
        # "brand_id + indication_id" → "indication_id"
        pk_col = pk_raw.split("+")[-1].strip() if "+" in pk_raw else pk_raw
        pks[name] = pk_col

    return pks


def get_edges(
    documentation_file: Path,
) -> list[tuple[str, str, str, str, str, float]]:
    """
    Parse the Section 3 relationships table and return a list of tuples:
        (source_table, source_column, target_table, target_column,
         relation_type, confidence)

    relation_type is:
      - "documented_self_fk"  when source_table == target_table  (confidence 0.95)
      - "documented_fk"       for all other FK relationships      (confidence 1.0)
    """
    doc = Document(str(documentation_file))
    table = doc.tables[_RELATIONSHIPS_TABLE_INDEX]
    rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]

    header = [col.lower() for col in rows[0]]
    col_src_table = header.index("from table")
    col_src_col   = header.index("from column")
    col_tgt_table = header.index("to table")
    col_tgt_col   = header.index("to column")

    edges: list[tuple[str, str, str, str, str, float]] = []
    for row in rows[1:]:
        src_table = row[col_src_table]
        if not src_table:
            continue
        src_col   = row[col_src_col]
        tgt_table = row[col_tgt_table]
        tgt_col   = row[col_tgt_col]

        if src_table == tgt_table:
            edges.append((src_table, src_col, tgt_table, tgt_col, "documented_self_fk", 0.95))
        else:
            edges.append((src_table, src_col, tgt_table, tgt_col, "documented_fk", 1.0))

    return edges


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

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

def rebuild_metadata(conn: sqlite3.Connection, table_roles: dict, primary_keys: dict, edges: list) -> dict:
    create_metadata_schema(conn)

    conn.execute("DELETE FROM _metadata_tables")
    conn.execute("DELETE FROM _metadata_columns")
    conn.execute("DELETE FROM _metadata_foreign_keys")
    conn.execute("DELETE FROM _metadata_semantic_columns")

    tables_in_db = existing_tables(conn)
    managed_tables = sorted([t for t in table_roles if t in tables_in_db])

    for table in managed_tables:
        cols_info = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
        row_count = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        pk_col = primary_keys.get(table)

        conn.execute("""
            INSERT INTO _metadata_tables(table_name, table_role, row_count, column_count, primary_key_column)
            VALUES (?, ?, ?, ?, ?)
        """, (table, table_roles.get(table), row_count, len(cols_info), pk_col))

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
    for s_table, s_col, t_table, t_col, rel_type, conf in edges:
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

    data_folder_path = ROOT / "data"
    documentation_file = None
    for file in data_folder_path.iterdir():
        if file.is_file() and file.suffix == ".docx" and "Technical_Documentation" in file.name:
            documentation_file = file
            break
    if not documentation_file:
        raise FileNotFoundError(f"Documentation file not found in {data_folder_path}")

    table_roles = get_table_roles(documentation_file)
    primary_keys = get_primary_keys(documentation_file)
    edges = get_edges(documentation_file)

    with sqlite3.connect(str(db_path)) as conn:
        summary = rebuild_metadata(conn, table_roles, primary_keys, edges)
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