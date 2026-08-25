"""解析「病人剧本 / 完整病历」的工具，供后端多处复用。

本仓库把病例内容拆成两个相互独立的字段：

- ``patient_scenario`` —— 患者本人知道、能用口语说出的完整病历（含一般情况 / 主诉 /
  现病史 / 既往史 / 系统回顾 / 个人史 / 家族史 / 婚育史 / 月经史等）。**只喂给**
  ``patient_system_prompt``（标准化病人角色扮演），绝不展示给考生，绝不作为卡片简介。
- ``reference_answer`` —— 完整教学参考答案 + 结构化问答，供考官/判卷阶段使用。

考生的**开场信息**只由 ``derive_patient_brief`` 从 ``patient_scenario`` 派生出来：
`年龄 + 性别 + 核心症状`（贴近真实 OSCE 考前给考生的那一行，如「A 55-year-old man
presents with chest pain」）。除此之外的一切信息都应由学生通过问诊自己问出来。
"""

from __future__ import annotations

import re

# 病人剧本里可识别的小节标题
_SECTION_ORDER = ("一般情况", "主诉", "现病史", "既往史")


def _section(scenario: str, title: str) -> str:
    """取出病人剧本中指定 `### 标题` 小节的内容（去掉标题行）。

    小节终点为下一个 `###` / `##` 标题、或字符串结束。
    """
    if not scenario:
        return ""
    pattern = re.compile(
        rf"###\s*{re.escape(title)}\s*\n(.*?)(?=\n##|\n###|\Z)",
        re.DOTALL,
    )
    m = pattern.search(scenario)
    return m.group(1).strip() if m else ""


def parse_patient_scenario(scenario: str) -> dict:
    """把 ``patient_scenario`` 解析成结构化摘要，供 mock 病人按需作答。"""
    general = _section(scenario, "一般情况")
    complaint = _section(scenario, "主诉")

    age_m = re.search(r"(\d{1,3})\s*岁", general)
    gender_m = re.search(r"([男女])", general)

    duration = ""
    if complaint:
        d = re.search(r"(\d+\s*(?:天|小时|周|月|年))", complaint)
        if d:
            duration = d.group(1).strip()

    return {
        "age": age_m.group(1) if age_m else "",
        "gender": gender_m.group(1) if gender_m else "",
        "complaint": complaint,
        "duration": duration,
    }


def _gender_label(gender: str) -> str:
    if gender == "男":
        return "男性"
    if gender == "女":
        return "女性"
    return ""


def derive_patient_brief(patient_scenario: str) -> str:
    """派生考生的开场信息：`年龄 + 性别 + 核心症状`。

    只取这三样，不包含任何病史细节 / 诊断 / 查体 / 检查结果。派生失败时返回空串。
    """
    scenario = (patient_scenario or "").strip()
    if not scenario:
        return ""

    info = parse_patient_scenario(scenario)
    if info["complaint"]:
        # 结构化病人剧本：从 一般情况/主诉 提取
        head: list[str] = []
        if info["age"]:
            head.append(f"{info['age']}岁")
        label = _gender_label(info["gender"])
        if label:
            head.append(label)
        head_str = "，".join(head)
        return f"{head_str}，{info['complaint']}" if head_str else info["complaint"]

    # 自由文本（无 一般情况/主诉 小节，如 GP-003）：取年龄+性别+主诉短语
    age_m = re.search(r"(\d{1,3})\s*岁", scenario)
    gender_m = re.search(r"([男女])", scenario)
    head = []
    if age_m:
        head.append(f"{age_m.group(1)}岁")
    label = _gender_label(gender_m.group(1) if gender_m else "")
    if label:
        head.append(label)
    head_str = "，".join(head)

    # 主诉短语：紧跟「N岁」之后的第一个短句（到下一个逗号/句号为止）
    symptom = ""
    if age_m:
        rest = scenario[age_m.end():].lstrip("，,。 ")
        symptom = re.split(r"[，。]", rest, maxsplit=1)[0].strip()
    else:
        symptom = re.split(r"[，。]", scenario)[0].strip()

    return f"{head_str}，{symptom}" if head_str else symptom
