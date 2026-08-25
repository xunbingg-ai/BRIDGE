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
        _migrate_cases(conn)
        seed_admin(conn)
        count = conn.execute("SELECT COUNT(*) AS n FROM cases").fetchone()["n"]
        if count == 0:
            seed_cases(conn)
        conn.commit()
    finally:
        conn.close()


def _migrate_cases(conn: sqlite3.Connection) -> None:
    """把旧版 cases 表迁移到新 schema。

    - 旧表含 difficulty / patient_prompt / examiner_prompt 三列，现已移除，就地删除列（幂等）。
    - 旧表把「病人剧本」放在 summary 列（曾被卡片/mock 直接暴露）。本迁移把该列改名为
      patient_scenario（内容不变），使卡片改用派生的 brief、病人仅按 prompt 回答。
      SQLite 3.25+ 支持 RENAME COLUMN。
    """
    columns = [row["name"] for row in conn.execute("PRAGMA table_info(cases)").fetchall()]
    for legacy in ("difficulty", "patient_prompt", "examiner_prompt"):
        if legacy in columns:
            conn.execute(f"ALTER TABLE cases DROP COLUMN {legacy}")
    if "summary" in columns and "patient_scenario" not in columns:
        conn.execute("ALTER TABLE cases RENAME COLUMN summary TO patient_scenario")


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
                case_no, title, department, patient_scenario, reference_answer, is_active
            ) VALUES (?, ?, ?, ?, ?, 1)
            """,
            (
                case["case_no"],
                case["title"],
                case["department"],
                case["patient_scenario"],
                case["reference_answer"],
            ),
        )
