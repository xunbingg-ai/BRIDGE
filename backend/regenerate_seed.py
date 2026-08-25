"""用 case_content/_compiled.json 的内容重组 seed_data.py（13 例）。

- 12 例：保留现有 case_no/title/department，替换 patient_scenario/reference_answer。
- GP-003：从 osce.db 读取（它是手工入库的参考病例，不在 seed_data.py），一并写入，
  使从零 seed 时病例库恢复为 13 例。
- 输出到 seed_data.py（覆盖）。仅当 _compiled.json 已包含全部 12 例时才写入。

用法:
    ./.venv/bin/python regenerate_seed.py --dry-run   # 只打印，不写
    ./.venv/bin/python regenerate_seed.py             # 写 seed_data.py
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COMPILED = os.path.join(BASE_DIR, "..", "case_content", "_compiled.json")
DB_PATH = os.path.join(BASE_DIR, "osce.db")
SEED_PATH = os.path.join(BASE_DIR, "seed_data.py")

CASES_ORDER = [
    "IM-001", "IM-002", "SG-001", "SG-002", "OG-001", "OG-002",
    "PD-001", "PD-002", "GP-001", "GP-002", "PS-001", "PS-002",
]

EXPECTED = set(CASES_ORDER)


def main() -> None:
    dry = "--dry-run" in sys.argv
    with open(COMPILED, "r", encoding="utf-8") as f:
        compiled = json.load(f)

    missing = EXPECTED - set(compiled.keys())
    if missing:
        print(f"[!] 仍有缺失 case，中止: {sorted(missing)}")
        sys.exit(1)

    # 载入现有 seed_data.CASES 以保留 meta
    sys.path.insert(0, BASE_DIR)
    from seed_data import CASES  # noqa: E402

    meta = {c["case_no"]: c for c in CASES}

    # 从 DB 读 GP-003 meta
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    gp = conn.execute(
        "SELECT case_no, title, department, patient_scenario, reference_answer "
        "FROM cases WHERE case_no='GP-003'"
    ).fetchone()
    conn.close()
    if gp is None:
        print("[!] DB 中无 GP-003，中止")
        sys.exit(1)
    gp_meta = {
        "case_no": gp["case_no"],
        "title": gp["title"],
        "department": gp["department"],
        "patient_scenario": gp["patient_scenario"],
        "reference_answer": gp["reference_answer"],
    }

    # 组装最终列表：12 例（替换内容）+ GP-003
    ordered: list[dict] = []
    for case_no in CASES_ORDER:
        m = meta[case_no]
        ordered.append({
            "case_no": m["case_no"],
            "title": m["title"],
            "department": m["department"],
            "patient_scenario": compiled[case_no]["patient_scenario"],
            "reference_answer": compiled[case_no]["reference_answer"],
        })
    ordered.append(gp_meta)

    if dry:
        for c in ordered:
            print(f"{c['case_no']:<8} patient_scenario={len(c['patient_scenario']):>5} ref={len(c['reference_answer']):>5}")
        print("dry-run，未写 seed_data.py")
        return

    # 生成 seed_data.py
    lines = ["CASES = ["]
    for c in ordered:
        lines.append("    {")
        lines.append(f"        \"case_no\": {json.dumps(c['case_no'], ensure_ascii=False)},")
        lines.append(f"        \"title\": {json.dumps(c['title'], ensure_ascii=False)},")
        lines.append(f"        \"department\": {json.dumps(c['department'], ensure_ascii=False)},")
        lines.append(f"        \"patient_scenario\": {json.dumps(c['patient_scenario'], ensure_ascii=False)},")
        lines.append(f"        \"reference_answer\": {json.dumps(c['reference_answer'], ensure_ascii=False)},")
        lines.append("    },")
    lines.append("]")
    with open(SEED_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"已写 {len(ordered)} 例 -> {SEED_PATH}")


if __name__ == "__main__":
    main()
