from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from local_db import DEFAULT_DB_PATH


class DatabaseService:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._project_root = Path(__file__).resolve().parents[2]

    # Internal helper to reduce boilerplate
    def _run_query(self, query: str, params: tuple = (), fetch: bool = True) -> list[dict[str, Any]]:
        """
        Opens, executes, and closes connection automatically.
        Returns results as a list of dictionaries for better modularity.
        """
        with sqlite3.connect(self.db_path) as conn:
            # This allows accessing columns by name: row['title'] instead of row[0]
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            if fetch:
                return [dict(row) for row in cursor.fetchall()]
            conn.commit()
            return []

    def retrieve_tables(self) -> list[str]:
        rows = self._run_query("SELECT name FROM sqlite_master WHERE type='table';")
        return [r['name'] for r in rows if r['name'] not in {'sqlite_sequence'} and not r['name'].startswith('_metadata_')]

    def get_schema_metadata(self) -> tuple[list[str], list[tuple[str, str]]]:
        nodes = self.retrieve_tables()
        edges = []

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            metadata_fk_exists = cursor.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type='table' AND name='_metadata_foreign_keys'
                """
            ).fetchone() is not None

            if metadata_fk_exists:
                fk_rows = cursor.execute(
                    """
                    SELECT source_table, target_table
                    FROM _metadata_foreign_keys
                    """
                ).fetchall()
                edges = [(r["source_table"], r["target_table"]) for r in fk_rows if r["source_table"] in nodes and r["target_table"] in nodes]
            else:
                for table in nodes:
                    cursor.execute(f"PRAGMA foreign_key_list('{table}');")
                    for fk in cursor.fetchall():
                        # fk[2] is the remote table name
                        edges.append((table, fk[2]))
        return nodes, edges

    def execute_query(self, query: str, params: tuple = ()) -> list[dict[str, Any]]:
        """
        Executes a generated SQL query. Use params to prevent SQL injection.
        """
        cleaned = query.strip().rstrip(";").lstrip()
        if not cleaned.lower().startswith("select"):
            return [{"error": f"Refused to execute non-SELECT query: {query}"}]
        try:
            return self._run_query(query, params, fetch=True)
        except sqlite3.Error as e:
            print(f"Database Error: {e}")
            return [{"error": str(e)}]

    def retrieve_schema_for_prompt(self, tables: list[str]) -> str:
        """
        Given a list of tables, return a formatted string with their columns for LLM context.
        :param tables: List of table names to retrieve schema for.
        :return: Formatted string describing the tables and their columns, e.g.:
        """
        schema_info = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for table in tables:
                cursor.execute(f"PRAGMA table_info('{table}');")
                columns = [col[1] for col in cursor.fetchall()]
                # Format: "Table books: id, title, author_id"
                schema_info.append(f"Table {table}: {', '.join(columns)}")

        return "\n".join(schema_info)

    def _metadata_fk_exists(self, conn: sqlite3.Connection) -> bool:
        row = conn.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type='table' AND name='_metadata_foreign_keys'
            """
        ).fetchone()
        return row is not None

    def _table_exists(self, conn: sqlite3.Connection, table_name: str) -> bool:
        row = conn.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type='table' AND name=?
            """,
            (table_name,),
        ).fetchone()
        return row is not None

    def _get_foreign_keys_for_table(self, conn: sqlite3.Connection, table: str) -> list[dict[str, str]]:
        if self._metadata_fk_exists(conn):
            rows = conn.execute(
                """
                SELECT source_column, target_table, target_column
                FROM _metadata_foreign_keys
                WHERE source_table = ?
                ORDER BY source_column, target_table, target_column
                """,
                (table,),
            ).fetchall()
            return [
                {
                    "source_column": r[0],
                    "target_table": r[1],
                    "target_column": r[2],
                }
                for r in rows
            ]

        pragma_rows = conn.execute(f"PRAGMA foreign_key_list('{table}')").fetchall()
        return [
            {
                "source_column": r[3],  # from
                "target_table": r[2],   # table
                "target_column": r[4],  # to
            }
            for r in pragma_rows
        ]

    def retrieve_structured_schema_context(
        self,
        tables: list[str] | None = None,
        sample_rows_per_table: int = 2,
    ) -> str:
        """
        Build compact, structured schema context for LLMs:
        - table name
        - columns with sqlite type and PK marker
        - FK relationships
        - example records (few rows)
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if tables:
                selected_tables = sorted(set(tables))
            else:
                selected_tables = sorted(self.retrieve_tables())

            lines: list[str] = []
            lines.append("DATABASE SCHEMA CONTEXT")
            lines.append("Use only the tables/columns shown below.")
            lines.append("")

            for table in selected_tables:
                if not self._table_exists(conn, table):
                    continue

                cols = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
                fks = self._get_foreign_keys_for_table(conn, table)
                role = "fact" if table.startswith("FACT_") else "dimension" if table.startswith("DIM_") else "table"

                lines.append(f"Table: {table} (type: {role})")
                lines.append("Columns:")
                for col in cols:
                    col_name = col["name"]
                    col_type = col["type"] or "TEXT"
                    pk_marker = " [PK]" if col["pk"] else ""
                    lines.append(f"- {col_name}: {col_type}{pk_marker}")

                lines.append("Foreign Keys:")
                if fks:
                    for fk in fks:
                        lines.append(
                            f"- {fk['source_column']} -> {fk['target_table']}.{fk['target_column']}"
                        )
                else:
                    lines.append("- (none)")

                lines.append("Sample Rows:")
                if sample_rows_per_table <= 0:
                    lines.append("- (disabled)")
                else:
                    sample_rows = conn.execute(
                        f'SELECT * FROM "{table}" LIMIT {int(sample_rows_per_table)}'
                    ).fetchall()
                    if not sample_rows:
                        lines.append("- (no rows)")
                    else:
                        for row in sample_rows:
                            row_dict = dict(row)
                            lines.append(f"- {row_dict}")
                lines.append("")

            return "\n".join(lines).strip()

    def get_schema_context_file_path(self) -> Path:
        return self._project_root / "data" / "documentation.txt"

    def build_and_save_schema_context_file(self, sample_rows_per_table: int = 2) -> str:
        context = self.retrieve_structured_schema_context(
            tables=self.retrieve_tables(),
            sample_rows_per_table=sample_rows_per_table,
        )
        out_path = self.get_schema_context_file_path()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(context, encoding="utf-8")
        return context

