from __future__ import annotations

import os
import sqlite3
from datetime import datetime

from werkzeug.security import generate_password_hash

from seed_data import CASES

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "osce.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = f.read()

    conn = get_db()
    try:
        conn.executescript(schema)
        seed_admin(conn)
        count = conn.execute("SELECT COUNT(*) AS n FROM cases").fetchone()["n"]
        if count == 0:
            seed_cases(conn)
        conn.commit()
    finally:
        conn.close()


def seed_admin(conn: sqlite3.Connection) -> None:
    admin = conn.execute(
        "SELECT user_id FROM users WHERE role = 'admin' LIMIT 1"
    ).fetchone()
    if admin:
        return

    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "admin123")
    conn.execute(
        """
        INSERT INTO users (username, password_hash, role)
        VALUES (?, ?, 'admin')
        """,
        (username, generate_password_hash(password)),
    )


def seed_cases(conn: sqlite3.Connection) -> None:
    for case in CASES:
        conn.execute(
            """
            INSERT INTO cases (
                case_no, title, department, summary, difficulty,
                patient_prompt, examiner_prompt, reference_answer, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                case["case_no"],
                case["title"],
                case["department"],
                case["summary"],
                case.get("difficulty", 2),
                case["patient_prompt"],
                case["examiner_prompt"],
                case["reference_answer"],
            ),
        )
