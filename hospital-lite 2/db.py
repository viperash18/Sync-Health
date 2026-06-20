"""
db.py — the only file that talks to SQLite directly.

Why a thin hand-written layer instead of an ORM?
  - Every query is plain SQL you can read and explain in an interview.
  - We ALWAYS pass user values as parameters (the `?` placeholders), never by
    string-formatting them into the SQL. That is what prevents SQL injection.

Connection handling:
  - One connection per request, stored on Flask's `g` object, closed at the end
    of the request (see app.py teardown). This avoids opening a new file handle
    on every query while staying simple.
  - row_factory = sqlite3.Row lets us read columns by name: row["email"].
"""

import sqlite3
from flask import g, current_app


def get_db():
    """Return the request-scoped connection, creating it on first use."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        # SQLite disables foreign-key enforcement by default; turn it on.
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(exception=None):
    """Close the connection at the end of the request (registered in app.py)."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create all tables from schema.sql. Safe to run repeatedly (IF NOT EXISTS)."""
    db = get_db()
    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf-8"))
    db.commit()


# --- tiny query helpers so routes read cleanly ---------------------------------

def query(sql, params=(), one=False):
    """Run a SELECT. Returns a list of rows, or a single row if one=True."""
    cur = get_db().execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows


def execute(sql, params=()):
    """Run an INSERT/UPDATE/DELETE. Commits and returns the new row id."""
    db = get_db()
    cur = db.execute(sql, params)
    db.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id
