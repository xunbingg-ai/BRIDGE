"""把 case_content/<case_no>.md 编译成统一的内容字典（patient_scenario + reference_answer）。

供 captain 在合并 12 个子代理产出时使用。只读 case_content/*.md，输出 JSON 与
每例的字段长度摘要，便于人工核对后再写入 seed_data.py / osce.db。

用法:
    ./.venv/bin/python compile_case_content.py
"""

from __future__ import annotations

import json
import os
import re

CONTENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "case_content")


def parse_case_md(path: str) -> dict | None:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # 定位两个顶层区块（病人剧本 + 参考答案）
    m_summary = re.search(r"^##\s*(?:SUMMARY|PATIENT_SCENARIO)\s*$", text, re.MULTILINE)
    m_ref = re.search(r"^##\s*REFERENCE_ANSWER\s*$", text, re.MULTILINE)
    if not (m_summary and m_ref):
        return None

    patient = text[m_summary.end(): m_ref.start()].strip()
    reference = text[m_ref.end():].strip()
    return {"patient_scenario": patient, "reference_answer": reference}


def main() -> None:
    results: dict[str, dict] = {}
    if os.path.isdir(CONTENT_DIR):
        for fn in sorted(os.listdir(CONTENT_DIR)):
            if not fn.endswith(".md") or fn.startswith("_"):
                continue
            case_no = fn[:-3]
            parsed = parse_case_md(os.path.join(CONTENT_DIR, fn))
            if parsed is None:
                print(f"[WARN] {fn}: 缺少 SUMMARY/REFERENCE_ANSWER 区块，跳过")
                continue
            results[case_no] = parsed

    out_path = os.path.join(CONTENT_DIR, "_compiled.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"编译完成，共 {len(results)} 例 -> {out_path}")
    for case_no in sorted(results):
        s = results[case_no]["patient_scenario"]
        r = results[case_no]["reference_answer"]
        print(f"  {case_no:<8} patient_scenario={len(s):>5}  reference={len(r):>5}")
    missing = [c for c in (
        "IM-001", "IM-002", "SG-001", "SG-002", "OG-001", "OG-002",
        "PD-001", "PD-002", "GP-001", "GP-002", "PS-001", "PS-002",
    ) if c not in results]
    if missing:
        print(f"[!] 以下 case 尚未产出: {missing}")


if __name__ == "__main__":
    main()
