from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from typing import Any, Iterable, Sequence


@dataclass(frozen=True)
class LocalDBConfig:
    """
    Configuration for the local SQLite database.
    """

    db_path: str


DEFAULT_DB_PATH = os.environ.get("JJC_DB_PATH", "./local.db")


SCHEMA_SQL = [
    """
    CREATE TABLE IF NOT EXISTS authors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author_id INTEGER NOT NULL,
        year INTEGER,
        FOREIGN KEY(author_id) REFERENCES authors(id),
        UNIQUE(title, author_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        text TEXT NOT NULL,
        FOREIGN KEY(book_id) REFERENCES books(id)
    );
    """,
]


SEED_DATA_SQL: list[tuple[str, Sequence[Any]]] = [
    ("INSERT OR IGNORE INTO authors(name) VALUES (?)", ("Isaac Asimov",)),
    ("INSERT OR IGNORE INTO authors(name) VALUES (?)", ("J.R.R. Tolkien",)),
    ("INSERT OR IGNORE INTO authors(name) VALUES (?)", ("Jane Austen",)),
    ("INSERT OR IGNORE INTO authors(name) VALUES (?)", ("Leo Tolstoy",)),
]


BOOKS_SEED: list[tuple[str, Sequence[Any]]] = [
    # Asimov
    ("INSERT OR IGNORE INTO books(title, author_id, year) VALUES (?, (SELECT id FROM authors WHERE name=?), ?)",
     ("I, Robot", "Isaac Asimov", 1950)),
    ("INSERT OR IGNORE INTO books(title, author_id, year) VALUES (?, (SELECT id FROM authors WHERE name=?), ?)",
     ("Foundation", "Isaac Asimov", 1951)),
    # Tolkien
    ("INSERT OR IGNORE INTO books(title, author_id, year) VALUES (?, (SELECT id FROM authors WHERE name=?), ?)",
     ("The Hobbit", "J.R.R. Tolkien", 1937)),
    ("INSERT OR IGNORE INTO books(title, author_id, year) VALUES (?, (SELECT id FROM authors WHERE name=?), ?)",
     ("The Lord of the Rings", "J.R.R. Tolkien", 1954)),
    # Austen
    ("INSERT OR IGNORE INTO books(title, author_id, year) VALUES (?, (SELECT id FROM authors WHERE name=?), ?)",
     ("Pride and Prejudice", "Jane Austen", 1813)),
    # Tolstoy
    ("INSERT OR IGNORE INTO books(title, author_id, year) VALUES (?, (SELECT id FROM authors WHERE name=?), ?)",
     ("War and Peace", "Leo Tolstoy", 1869)),
]


REVIEWS_SEED: list[tuple[str, Sequence[Any]]] = [
    # I, Robot
    ("INSERT INTO reviews(book_id, rating, text) VALUES ((SELECT id FROM books WHERE title=?), ?, ?)",
     ("I, Robot", 5, "Clever stories that still feel modern.")),
    ("INSERT INTO reviews(book_id, rating, text) VALUES ((SELECT id FROM books WHERE title=?), ?, ?)",
     ("I, Robot", 4, "Great ideas, readable pacing.")),
    # Foundation
    ("INSERT INTO reviews(book_id, rating, text) VALUES ((SELECT id FROM books WHERE title=?), ?, ?)",
     ("Foundation", 5, "Strong world-building and memorable concepts.")),
    # The Hobbit
    ("INSERT INTO reviews(book_id, rating, text) VALUES ((SELECT id FROM books WHERE title=?), ?, ?)",
     ("The Hobbit", 5, "A cozy adventure with real heart.")),
    ("INSERT INTO reviews(book_id, rating, text) VALUES ((SELECT id FROM books WHERE title=?), ?, ?)",
     ("The Hobbit", 4, "Fun and fast; the magic lands.")),
    # Pride and Prejudice
    ("INSERT INTO reviews(book_id, rating, text) VALUES ((SELECT id FROM books WHERE title=?), ?, ?)",
     ("Pride and Prejudice", 5, "Witty dialogue and timeless themes.")),
    # War and Peace
    ("INSERT INTO reviews(book_id, rating, text) VALUES ((SELECT id FROM books WHERE title=?), ?, ?)",
     ("War and Peace", 4, "Big cast, deep history, worth the effort.")),
]


def connect(db_path: str) -> sqlite3.Connection:
    # Ensure folder exists (if user chooses a path with directories).
    folder = os.path.dirname(os.path.abspath(db_path))
    if folder and not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # Foreign keys are useful for debugging schema issues.
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_schema_and_seed(conn: sqlite3.Connection) -> None:
    for stmt in SCHEMA_SQL:
        conn.execute(stmt)

    for stmt, params in SEED_DATA_SQL:
        conn.execute(stmt, params)

    for stmt, params in BOOKS_SEED:
        conn.execute(stmt, params)

    reviews_count = conn.execute("SELECT COUNT(*) AS c FROM reviews;").fetchone()["c"]
    if reviews_count == 0:
        for stmt, params in REVIEWS_SEED:
            conn.execute(stmt, params)

    conn.commit()


def fetch_table_schemas(conn: sqlite3.Connection, table_names: Iterable[str]) -> str:
    parts: list[str] = []
    for name in table_names:
        row = conn.execute(
            """
            SELECT sql
            FROM sqlite_master
            WHERE type='table' AND name=?
            """,
            (name,),
        ).fetchone()
        if row and row["sql"]:
            parts.append(row["sql"])
    return "\n\n".join(parts).strip()


def execute_query(conn: sqlite3.Connection, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    return [dict(r) for r in rows]

