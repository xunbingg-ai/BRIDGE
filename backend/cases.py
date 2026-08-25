from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from case_utils import derive_patient_brief

bp = Blueprint("cases", __name__, url_prefix="/api/cases")

DEPARTMENTS = {"internal", "surgery", "obgyn", "pediatrics", "general", "psychiatry"}


def case_to_dict(case) -> dict:
    """公开列表 / 公共详情用：只暴露卡片所需的 OSCE 开场信息（派生 brief）。

    绝不暴露 patient_scenario（完整病人剧本）或 reference_answer（参考答案），它们只在
    后端 prompt / 报告页（经 session 接口）使用，不提供给考生端病例列表。
    """
    return {
        "caseId": case["case_id"],
        "caseNo": case["case_no"],
        "title": case["title"],
        "department": case["department"],
        "brief": case["brief"] or derive_patient_brief(case["patient_scenario"] or "", case["case_no"]),
        "createdAt": case["created_at"],
        "updatedAt": case["updated_at"],
    }


def case_detail_to_dict(case) -> dict:
    """管理后台详情用：暴露完整病人剧本 + 参考答案，供管理员编辑。"""
    data = case_to_dict(case)
    data["patientScenario"] = case["patient_scenario"]
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
        where.append("(title LIKE ? OR patient_scenario LIKE ? OR case_no LIKE ?)")
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
    # 公共详情不暴露病人剧本 / 参考答案，只返回卡片开场信息。
    return jsonify({"case": case_to_dict(case)})
