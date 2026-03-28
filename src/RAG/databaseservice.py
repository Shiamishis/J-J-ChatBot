import sqlite3
from typing import Any, Dict, List
from local_db import DEFAULT_DB_PATH

class DatabaseService:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path

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
        return [r['name'] for r in rows if r['name'] != 'sqlite_sequence']

    def get_schema_metadata(self) -> tuple[list[str], list[tuple[str, str]]]:
        nodes = self.retrieve_tables()
        edges = []

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
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
