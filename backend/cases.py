from __future__ import annotations

from flask import Blueprint, g, jsonify, request

bp = Blueprint("cases", __name__, url_prefix="/api/cases")

DEPARTMENTS = {"internal", "surgery", "obgyn", "pediatrics", "general", "psychiatry"}


def case_to_dict(case) -> dict:
    return {
        "caseId": case["case_id"],
        "caseNo": case["case_no"],
        "title": case["title"],
        "department": case["department"],
        "summary": case["summary"],
        "difficulty": case["difficulty"],
        "createdAt": case["created_at"],
        "updatedAt": case["updated_at"],
    }


def case_detail_to_dict(case) -> dict:
    data = case_to_dict(case)
    data["patientPrompt"] = case["patient_prompt"]
    data["examinerPrompt"] = case["examiner_prompt"]
    data["referenceAnswer"] = case["reference_answer"]
    data["isActive"] = case["is_active"]
    return data


@bp.get("")
def list_cases():
    department = (request.args.get("department") or "all").strip().lower()
    search = (request.args.get("search") or "").strip()
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("pageSize", 8)), 1), 50)

    where = ["is_active = 1"]
    params: list = []

    if department != "all":
        if department not in DEPARTMENTS:
            return jsonify({"message": "无效的病例门类"}), 400
        where.append("department = ?")
        params.append(department)

    if search:
        where.append("(title LIKE ? OR summary LIKE ? OR case_no LIKE ?)")
        keyword = f"%{search}%"
        params.extend([keyword, keyword, keyword])

    where_sql = " AND ".join(where)
    total = g.db.execute(
        f"SELECT COUNT(*) AS n FROM cases WHERE {where_sql}", params
    ).fetchone()["n"]

    offset = (page - 1) * page_size
    rows = g.db.execute(
        f"""
        SELECT * FROM cases
        WHERE {where_sql}
        ORDER BY case_id ASC
        LIMIT ? OFFSET ?
        """,
        [*params, page_size, offset],
    ).fetchall()

    return jsonify(
        {
            "items": [case_to_dict(row) for row in rows],
            "total": total,
            "page": page,
            "pageSize": page_size,
        }
    )


@bp.get("/<int:case_id>")
def get_case(case_id: int):
    case = g.db.execute(
        "SELECT * FROM cases WHERE case_id = ? AND is_active = 1", (case_id,)
    ).fetchone()
    if case is None:
        return jsonify({"message": "病例不存在"}), 404
    return jsonify({"case": case_detail_to_dict(case)})
