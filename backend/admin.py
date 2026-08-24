from __future__ import annotations

import csv
import io
from datetime import datetime

from flask import Blueprint, g, jsonify, request, Response

import llm_config
from auth import admin_required
from cases import case_detail_to_dict
from database import now_iso

bp = Blueprint("admin", __name__, url_prefix="/api/admin")

DEPARTMENTS = {"internal", "surgery", "obgyn", "pediatrics", "general", "psychiatry"}

CSV_FIELDS = [
    "case_no",
    "title",
    "department",
    "summary",
    "difficulty",
    "patient_prompt",
    "examiner_prompt",
    "reference_answer",
]


def _validate_case_payload(data: dict, partial: bool = False) -> tuple[dict, str | None]:
    title = (data.get("title") or "").strip()
    department = (data.get("department") or "").strip().lower()
    summary = (data.get("summary") or "").strip()
    patient_prompt = (data.get("patientPrompt") or data.get("patient_prompt") or "").strip()
    examiner_prompt = (data.get("examinerPrompt") or data.get("examiner_prompt") or "").strip()
    reference_answer = (data.get("referenceAnswer") or data.get("reference_answer") or "").strip()

    if not partial or "title" in data:
        if not title:
            return {}, "病例标题不能为空"
    if not partial or "department" in data:
        if department not in DEPARTMENTS:
            return {}, "无效的病例门类"

    difficulty_raw = data.get("difficulty", 2)
    try:
        difficulty = int(difficulty_raw)
    except (TypeError, ValueError):
        return {}, "难度必须是1-3的整数"
    if difficulty not in {1, 2, 3}:
        return {}, "难度必须是1-3的整数"

    if not patient_prompt:
        return {}, "AI病人提示词不能为空"
    if not examiner_prompt:
        return {}, "AI考官提示词不能为空"
    if not reference_answer:
        return {}, "参考答案不能为空"

    case_no = (data.get("caseNo") or data.get("case_no") or "").strip()
    return {
        "case_no": case_no,
        "title": title,
        "department": department,
        "summary": summary,
        "difficulty": difficulty,
        "patient_prompt": patient_prompt,
        "examiner_prompt": examiner_prompt,
        "reference_answer": reference_answer,
    }, None


def _generate_case_no() -> str:
    return f"CASE-{datetime.now().strftime('%Y%m%d%H%M%S')}"


@bp.get("/cases")
@admin_required
def list_admin_cases():
    search = (request.args.get("search") or "").strip()
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("pageSize", 100)), 1), 500)

    where = ""
    params: list = []
    if search:
        where = "WHERE title LIKE ? OR summary LIKE ? OR case_no LIKE ?"
        keyword = f"%{search}%"
        params = [keyword, keyword, keyword]

    total = g.db.execute(f"SELECT COUNT(*) AS n FROM cases {where}", params).fetchone()["n"]
    rows = g.db.execute(
        f"""
        SELECT * FROM cases
        {where}
        ORDER BY case_id DESC
        LIMIT ? OFFSET ?
        """,
        [*params, page_size, (page - 1) * page_size],
    ).fetchall()

    return jsonify(
        {
            "items": [case_detail_to_dict(row) for row in rows],
            "total": total,
            "page": page,
            "pageSize": page_size,
        }
    )


@bp.get("/cases/<int:case_id>")
@admin_required
def get_admin_case(case_id: int):
    row = g.db.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
    if row is None:
        return jsonify({"message": "病例不存在"}), 404
    return jsonify({"case": case_detail_to_dict(row)})


@bp.post("/cases")
@admin_required
def create_case():
    payload, error = _validate_case_payload(request.get_json(silent=True) or {})
    if error:
        return jsonify({"message": error}), 400

    case_no = payload["case_no"] or _generate_case_no()
    exists = g.db.execute("SELECT case_id FROM cases WHERE case_no = ?", (case_no,)).fetchone()
    if exists:
        return jsonify({"message": "病例编号已存在"}), 409

    cursor = g.db.execute(
        """
        INSERT INTO cases (
            case_no, title, department, summary, difficulty,
            patient_prompt, examiner_prompt, reference_answer, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            case_no,
            payload["title"],
            payload["department"],
            payload["summary"],
            payload["difficulty"],
            payload["patient_prompt"],
            payload["examiner_prompt"],
            payload["reference_answer"],
        ),
    )
    g.db.commit()

    row = g.db.execute("SELECT * FROM cases WHERE case_id = ?", (cursor.lastrowid,)).fetchone()
    return jsonify({"case": case_detail_to_dict(row)}), 201


@bp.put("/cases/<int:case_id>")
@admin_required
def update_case(case_id: int):
    row = g.db.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
    if row is None:
        return jsonify({"message": "病例不存在"}), 404

    payload, error = _validate_case_payload(request.get_json(silent=True) or {}, partial=True)
    if error:
        return jsonify({"message": error}), 400

    case_no = payload["case_no"] or row["case_no"]
    duplicate = g.db.execute(
        "SELECT case_id FROM cases WHERE case_no = ? AND case_id != ?",
        (case_no, case_id),
    ).fetchone()
    if duplicate:
        return jsonify({"message": "病例编号已存在"}), 409

    g.db.execute(
        """
        UPDATE cases
        SET case_no = ?, title = ?, department = ?, summary = ?, difficulty = ?,
            patient_prompt = ?, examiner_prompt = ?, reference_answer = ?, updated_at = ?
        WHERE case_id = ?
        """,
        (
            case_no,
            payload["title"],
            payload["department"],
            payload["summary"],
            payload["difficulty"],
            payload["patient_prompt"],
            payload["examiner_prompt"],
            payload["reference_answer"],
            now_iso(),
            case_id,
        ),
    )
    g.db.commit()

    row = g.db.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
    return jsonify({"case": case_detail_to_dict(row)})


@bp.delete("/cases/<int:case_id>")
@admin_required
def delete_case(case_id: int):
    row = g.db.execute("SELECT case_id FROM cases WHERE case_id = ?", (case_id,)).fetchone()
    if row is None:
        return jsonify({"message": "病例不存在"}), 404

    g.db.execute("DELETE FROM cases WHERE case_id = ?", (case_id,))
    g.db.commit()
    return jsonify({"message": "病例已删除"})


@bp.post("/cases/batch-delete")
@admin_required
def batch_delete_cases():
    data = request.get_json(silent=True) or {}
    case_ids = data.get("caseIds") or data.get("case_ids") or []

    if not isinstance(case_ids, list) or not case_ids:
        return jsonify({"message": "请选择要删除的病例"}), 400

    try:
        case_ids = [int(item) for item in case_ids]
    except (TypeError, ValueError):
        return jsonify({"message": "病例ID格式错误"}), 400

    placeholders = ",".join("?" for _ in case_ids)
    cursor = g.db.execute(
        f"DELETE FROM cases WHERE case_id IN ({placeholders})",
        case_ids,
    )
    g.db.commit()
    return jsonify({"deleted": cursor.rowcount, "message": "批量删除完成"})


@bp.get("/cases/template.csv")
@admin_required
def download_case_template():
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
    writer.writeheader()
    writer.writerow(
        {
            "case_no": "",
            "title": "示例病例：发热伴咳嗽",
            "department": "internal",
            "summary": "男性，30岁，发热咳嗽3天。",
            "difficulty": "2",
            "patient_prompt": "你是一名30岁男性患者，请以患者视角回答。",
            "examiner_prompt": "你是OSCE考官，请追问诊断依据和治疗原则。",
            "reference_answer": "诊断：社区获得性肺炎；治疗：抗感染、对症支持。",
        }
    )
    csv_text = "\ufeff" + output.getvalue()
    return Response(
        csv_text,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=case_template.csv"},
    )


def _decode_csv(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "gbk"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


@bp.post("/cases/import")
@admin_required
def import_cases():
    file = request.files.get("file")
    if file is None or file.filename == "":
        return jsonify({"message": "请选择CSV文件"}), 400

    raw = file.read()
    text = _decode_csv(raw)
    reader = csv.DictReader(io.StringIO(text))

    inserted = 0
    updated = 0
    errors: list[dict] = []

    for line_no, row in enumerate(reader, start=2):
        payload, error = _validate_case_payload(row)
        if error:
            errors.append({"line": line_no, "message": error})
            continue

        case_no = payload["case_no"]
        existing = None
        if case_no:
            existing = g.db.execute(
                "SELECT case_id FROM cases WHERE case_no = ?", (case_no,)
            ).fetchone()

        if existing:
            g.db.execute(
                """
                UPDATE cases
                SET title = ?, department = ?, summary = ?, difficulty = ?,
                    patient_prompt = ?, examiner_prompt = ?, reference_answer = ?, updated_at = ?
                WHERE case_no = ?
                """,
                (
                    payload["title"],
                    payload["department"],
                    payload["summary"],
                    payload["difficulty"],
                    payload["patient_prompt"],
                    payload["examiner_prompt"],
                    payload["reference_answer"],
                    now_iso(),
                    case_no,
                ),
            )
            updated += 1
        else:
            g.db.execute(
                """
                INSERT INTO cases (
                    case_no, title, department, summary, difficulty,
                    patient_prompt, examiner_prompt, reference_answer, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    case_no or _generate_case_no(),
                    payload["title"],
                    payload["department"],
                    payload["summary"],
                    payload["difficulty"],
                    payload["patient_prompt"],
                    payload["examiner_prompt"],
                    payload["reference_answer"],
                ),
            )
            inserted += 1

    g.db.commit()
    return jsonify({"inserted": inserted, "updated": updated, "errors": errors})


def _filled_llm_input(data: dict, existing: dict | None) -> dict:
    headers = data.get("headers", existing.get("headers") if existing else {})
    if isinstance(headers, str):
        headers = llm_config._parse_headers(headers)
    return {
        "baseUrl": (data.get("baseUrl") or (existing or {}).get("baseUrl") or "").strip(),
        "apiKey": (data.get("apiKey") or (existing or {}).get("apiKey") or "").strip(),
        "headers": headers,
    }


@bp.get("/llm-config")
@admin_required
def get_llm_config():
    return jsonify({"config": llm_config.get_public_llm_config()})


@bp.put("/llm-config")
@admin_required
def save_llm_config_route():
    try:
        config = llm_config.save_llm_config(request.get_json(silent=True) or {})
        return jsonify({"config": config, "message": "配置已保存"})
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 400


@bp.post("/llm-config/models")
@admin_required
def fetch_llm_models():
    existing = llm_config.get_active_llm_config() or {}
    input_data = _filled_llm_input(request.get_json(silent=True) or {}, existing)
    if not input_data["baseUrl"]:
        return jsonify({"message": "请填写 Base URL"}), 400

    models, error = llm_config.fetch_model_list(
        input_data["baseUrl"],
        input_data["apiKey"],
        input_data["headers"],
    )
    if error:
        return jsonify({"message": error, "models": []}), 400
    return jsonify({"models": models})


@bp.post("/llm-config/test")
@admin_required
def test_llm_model():
    existing = llm_config.get_active_llm_config() or {}
    data = request.get_json(silent=True) or {}
    input_data = _filled_llm_input(data, existing)
    model = (data.get("model") or "").strip()
    if not input_data["baseUrl"]:
        return jsonify({"message": "请填写 Base URL"}), 400
    if not model:
        return jsonify({"message": "请选择模型"}), 400

    result, error = llm_config.test_model_speed(
        input_data["baseUrl"],
        input_data["apiKey"],
        input_data["headers"],
        model,
    )
    if error:
        return jsonify({"message": error, "result": result}), 400
    return jsonify({"result": result})
