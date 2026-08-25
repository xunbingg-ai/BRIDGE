from __future__ import annotations

import json
import threading
import traceback
from datetime import datetime

from flask import Blueprint, g, jsonify, request

import ai_service
from auth import token_required
from database import get_db, now_iso

bp = Blueprint("sessions", __name__, url_prefix="/api/sessions")


def _parse_json(value, fallback=None):
    if value in (None, ""):
        return fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def _json_dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def _now_datetime() -> datetime:
    return datetime.now().astimezone()


def _initial_content(session_id: int, case_id: int) -> dict:
    return {
        "session_id": session_id,
        "case_id": case_id,
        "started_at": now_iso(),
        "ended_at": None,
        "duration_seconds": 0,
        "patient_phase": [],
        "examiner_phase": [],
    }


def _append_message(content: dict, phase: str, role: str, text: str) -> dict:
    messages = content.setdefault(f"{phase}_phase", [])
    messages.append(
        {
            "id": len(messages) + 1,
            "role": role,
            "content": text,
            "created_at": now_iso(),
        }
    )
    return content


def _ai_messages(phase_messages: list[dict]) -> list[dict[str, str]]:
    return [
        {"role": m.get("role", "user"), "content": m.get("content", "")}
        for m in phase_messages
        if m.get("role") in {"user", "assistant"}
    ]


def _get_owned_session(session_id: int):
    return g.db.execute(
        """
        SELECT
            s.*,
            c.case_no AS case_no,
            c.title AS case_title,
            c.department AS case_department,
            c.summary AS case_summary,
            c.reference_answer AS case_reference_answer
        FROM sessions s
        JOIN cases c ON c.case_id = s.case_id
        WHERE s.session_id = ? AND s.user_id = ?
        """,
        (session_id, g.user["user_id"]),
    ).fetchone()


def _case_payload(row) -> dict:
    return {
        "case_id": row["case_id"],
        "case_no": row["case_no"],
        "title": row["case_title"],
        "department": row["case_department"],
        "summary": row["case_summary"],
        "reference_answer": row["case_reference_answer"],
    }


def session_to_dict(row, include_case: bool = False) -> dict:
    data = {
        "sessionId": row["session_id"],
        "userId": row["user_id"],
        "caseId": row["case_id"],
        "createAt": row["create_at"],
        "deadlineAt": row["deadline_at"],
        "status": row["status"],
        "content": _parse_json(row["content"], {}),
        "score": _parse_json(row["score"]),
        "report": _parse_json(row["report"]),
        "endedAt": row["ended_at"],
        "updatedAt": row["updated_at"],
    }
    if include_case:
        data.update(
            {
                "caseTitle": row["case_title"],
                "department": row["case_department"],
                "summary": row["case_summary"],
                "referenceAnswer": row["case_reference_answer"],
            }
        )
    return data


def history_to_dict(row) -> dict:
    score = _parse_json(row["score"], {})
    return {
        "sessionId": row["session_id"],
        "caseId": row["case_id"],
        "caseTitle": row["case_title"],
        "department": row["case_department"],
        "status": row["status"],
        "createAt": row["create_at"],
        "endedAt": row["ended_at"],
        "totalScore": score.get("total_score"),
    }


@bp.post("")
@token_required
def create_session():
    data = request.get_json(silent=True) or {}
    case_id = data.get("caseId") or data.get("caseid")

    if not case_id:
        return jsonify({"message": "缺少病例ID"}), 400

    case = g.db.execute(
        "SELECT * FROM cases WHERE case_id = ? AND is_active = 1", (case_id,)
    ).fetchone()
    if case is None:
        return jsonify({"message": "病例不存在"}), 404

    now = _now_datetime()
    cursor = g.db.execute(
        """
        INSERT INTO sessions (user_id, case_id, create_at, deadline_at, status, content, updated_at)
        VALUES (?, ?, ?, ?, 'patient', ?, ?)
        """,
        (
            g.user["user_id"],
            case_id,
            now.isoformat(timespec="seconds"),
            now.isoformat(timespec="seconds"),
            _json_dumps(_initial_content(0, case_id)),
            now.isoformat(timespec="seconds"),
        ),
    )
    session_id = cursor.lastrowid
    g.db.commit()

    row = _get_owned_session(session_id)
    content = _parse_json(row["content"], _initial_content(session_id, case_id))
    content["session_id"] = session_id
    reply = ai_service.patient_reply(_case_payload(row), _ai_messages(content["patient_phase"]))
    content = _append_message(content, "patient", "assistant", reply)

    g.db.execute(
        "UPDATE sessions SET content = ?, updated_at = ? WHERE session_id = ?",
        (_json_dumps(content), now_iso(), session_id),
    )
    g.db.commit()

    row = _get_owned_session(session_id)
    return jsonify(
        {
            "session": session_to_dict(row, include_case=True),
            "reply": reply,
            "phase": "patient",
        }
    ), 201


@bp.post("/<int:session_id>/message")
@token_required
def send_message(session_id: int):
    row = _get_owned_session(session_id)
    if row is None:
        return jsonify({"message": "会话不存在"}), 404
    if row["status"] not in {"patient", "examiner"}:
        return jsonify({"message": "当前会话已结束"}), 400

    data = request.get_json(silent=True) or {}
    user_text = (data.get("content") or "").strip()
    if not user_text:
        return jsonify({"message": "消息不能为空"}), 400

    content = _parse_json(row["content"], _initial_content(session_id, row["case_id"]))
    phase = row["status"]
    content = _append_message(content, phase, "user", user_text)

    if phase == "patient":
        reply = ai_service.patient_reply(_case_payload(row), _ai_messages(content["patient_phase"]))
    else:
        reply = ai_service.examiner_reply(_case_payload(row), _ai_messages(content["examiner_phase"]))

    content = _append_message(content, phase, "assistant", reply)
    g.db.execute(
        "UPDATE sessions SET content = ?, updated_at = ? WHERE session_id = ?",
        (_json_dumps(content), now_iso(), session_id),
    )
    g.db.commit()

    row = _get_owned_session(session_id)
    return jsonify(
        {
            "reply": reply,
            "phase": phase,
            "session": session_to_dict(row, include_case=True),
        }
    )


@bp.post("/<int:session_id>/end-inquiry")
@token_required
def end_inquiry(session_id: int):
    row = _get_owned_session(session_id)
    if row is None:
        return jsonify({"message": "会话不存在"}), 404
    if row["status"] != "patient":
        return jsonify({"message": "当前不在问询阶段"}), 400

    content = _parse_json(row["content"], _initial_content(session_id, row["case_id"]))
    content = _append_message(content, "patient", "system", "考生选择结束问询，进入考官审查阶段。")

    reply = ai_service.examiner_reply(_case_payload(row), _ai_messages(content.get("examiner_phase", [])))
    content = _append_message(content, "examiner", "assistant", reply)

    g.db.execute(
        "UPDATE sessions SET status = 'examiner', content = ?, updated_at = ? WHERE session_id = ?",
        (_json_dumps(content), now_iso(), session_id),
    )
    g.db.commit()

    row = _get_owned_session(session_id)
    return jsonify(
        {
            "reply": reply,
            "phase": "examiner",
            "session": session_to_dict(row, include_case=True),
        }
    )


def _grade_and_save(session_id: int) -> None:
    conn = get_db()
    try:
        row = conn.execute(
            """
            SELECT
                s.*,
                c.case_no AS case_no,
                c.title AS case_title,
                c.department AS case_department,
                c.summary AS case_summary,
                c.reference_answer AS case_reference_answer
            FROM sessions s
            JOIN cases c ON c.case_id = s.case_id
            WHERE s.session_id = ?
            """,
            (session_id,),
        ).fetchone()
        if row is None:
            return

        content = _parse_json(row["content"], {})
        score, report = ai_service.grade_session(_case_payload(row), content)
        now = now_iso()
        conn.execute(
            """
            UPDATE sessions
            SET status = 'completed', score = ?, report = ?, ended_at = ?, updated_at = ?
            WHERE session_id = ?
            """,
            (_json_dumps(score), _json_dumps(report), now, now, session_id),
        )
        conn.commit()
    except Exception:
        traceback.print_exc()
        try:
            conn.execute(
                "UPDATE sessions SET status = 'completed', report = ?, updated_at = ? WHERE session_id = ?",
                (
                    _json_dumps(
                        {
                            "summary": "评分过程中出现错误，请稍后重试或联系管理员。",
                            "strengths": [],
                            "weaknesses": [],
                            "suggestions": [],
                            "detailed_comments": [],
                        }
                    ),
                    now_iso(),
                    session_id,
                ),
            )
            conn.commit()
        except Exception:
            traceback.print_exc()
    finally:
        conn.close()


@bp.post("/<int:session_id>/submit")
@token_required
def submit_session(session_id: int):
    row = _get_owned_session(session_id)
    if row is None:
        return jsonify({"message": "会话不存在"}), 404
    if row["status"] != "examiner":
        return jsonify({"message": "请先结束问询并进入考官阶段"}), 400

    data = request.get_json(silent=True) or {}
    if data.get("content"):
        content = data["content"]
    else:
        content = _parse_json(row["content"], _initial_content(session_id, row["case_id"]))

    content = _append_message(content, "examiner", "system", "考生提交审查，等待评分。")
    now = now_iso()
    g.db.execute(
        """
        UPDATE sessions
        SET status = 'scoring', content = ?, ended_at = ?, updated_at = ?
        WHERE session_id = ?
        """,
        (_json_dumps(content), now, now, session_id),
    )
    g.db.commit()

    threading.Thread(target=_grade_and_save, args=(session_id,), daemon=True).start()
    return jsonify({"status": "scoring", "message": "已提交，正在评分中"})


@bp.get("")
@token_required
def list_sessions():
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("pageSize", 10)), 1), 50)

    total = g.db.execute(
        "SELECT COUNT(*) AS n FROM sessions WHERE user_id = ?", (g.user["user_id"],)
    ).fetchone()["n"]

    rows = g.db.execute(
        """
        SELECT
            s.session_id, s.case_id, s.status, s.create_at, s.ended_at, s.score,
            c.title AS case_title, c.department AS case_department
        FROM sessions s
        JOIN cases c ON c.case_id = s.case_id
        WHERE s.user_id = ?
        ORDER BY s.create_at DESC
        LIMIT ? OFFSET ?
        """,
        (g.user["user_id"], page_size, (page - 1) * page_size),
    ).fetchall()

    return jsonify(
        {
            "items": [history_to_dict(row) for row in rows],
            "total": total,
            "page": page,
            "pageSize": page_size,
        }
    )


@bp.get("/<int:session_id>")
@token_required
def get_session(session_id: int):
    row = _get_owned_session(session_id)
    if row is None:
        return jsonify({"message": "会话不存在"}), 404
    return jsonify({"session": session_to_dict(row, include_case=True)})
