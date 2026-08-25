PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    email TEXT UNIQUE,
    phone TEXT,
    real_name TEXT,
    avatar TEXT,
    role TEXT NOT NULL DEFAULT 'student',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS cases (
    case_id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_no TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    department TEXT NOT NULL CHECK (department IN ('internal', 'surgery', 'obgyn', 'pediatrics', 'general', 'psychiatry')),
    summary TEXT,
    reference_answer TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    case_id INTEGER NOT NULL,
    create_at TEXT NOT NULL,
    deadline_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'patient' CHECK (status IN ('patient', 'examiner', 'scoring', 'completed', 'expired')),
    content TEXT,
    score TEXT,
    report TEXT,
    ended_at TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_case ON sessions(case_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_created ON sessions(user_id, create_at DESC);
CREATE INDEX IF NOT EXISTS idx_cases_department ON cases(department);

CREATE TABLE IF NOT EXISTS llm_configs (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT NOT NULL DEFAULT '默认模型配置',
    base_url TEXT NOT NULL,
    api_key TEXT,
    headers_json TEXT,
    model TEXT,
    backup_model TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
