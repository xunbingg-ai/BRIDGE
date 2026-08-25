"""把 case_content/_compiled.json 的内容按 case_no 更新到 osce.db。

只覆盖 patient_scenario 与 reference_answer 两列，保留 title/department/is_active 与会话数据。
用法:
    ./.venv/bin/python update_case_content.py            # 全量（12 例）
    ./.venv/bin/python update_case_content.py --dry-run  # 只打印，不写库
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "osce.db")
COMPILED = os.path.join(BASE_DIR, "..", "case_content", "_compiled.json")


def main() -> None:
    dry = "--dry-run" in sys.argv
    with open(COMPILED, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    updated = 0
    for case_no, content in data.items():
        patient = content.get("patient_scenario", "")
        reference = content.get("reference_answer", "")
        row = conn.execute(
            "SELECT case_id, length(patient_scenario) AS s, length(reference_answer) AS r FROM cases WHERE case_no = ?",
            (case_no,),
        ).fetchone()
        if row is None:
            print(f"[SKIP] {case_no}: 数据库中不存在")
            continue
        if dry:
            print(f"[DRY]  {case_no}: 现 patient_scenario_len={row['s']} ref_len={row['r']} "
                  f"-> 新 patient_scenario_len={len(patient)} ref_len={len(reference)}")
            continue
        before = (row["s"], row["r"])
        conn.execute(
            "UPDATE cases SET patient_scenario = ?, reference_answer = ?, updated_at = datetime('now','localtime') WHERE case_no = ?",
            (patient, reference, case_no),
        )
        print(f"[OK]   {case_no}: {before} -> {(len(patient), len(reference))}")
        updated += 1

    if not dry:
        conn.commit()
    conn.close()
    print(f"共处理 {updated} 例（{'dry-run，未写库' if dry else '已写库'}）")


if __name__ == "__main__":
    main()
