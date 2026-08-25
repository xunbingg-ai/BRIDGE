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


# 每个内置病例在卡片上显示的「OSCE 开场信息」：`年龄 + 性别 + 一个核心症状`。
# 只保留最能练问题的主诉，**不带时间、不带过度精准的描述**（否则医学生一眼即知诊断，
# 失去练习价值）。卡片展示用；未收录的病例（如 CSV 导入）回退到派生结果。
CARD_BRIEFS: dict[str, str] = {
    "IM-001": "32岁，男性，发热咳嗽",
    "IM-002": "48岁，女性，多饮多尿",
    "SG-001": "24岁，男性，腹痛",
    "SG-002": "45岁，女性，右上腹痛",
    "OG-001": "28岁，女性，停经，腹痛",
    "OG-002": "32岁，女性，妊娠35周，头痛",
    "PD-001": "2岁，男性，腹泻",
    "PD-002": "8岁，男性，咳嗽喘息",
    "GP-001": "55岁，男性，血压升高",
    "GP-002": "40岁，女性，烧心反酸",
    "PS-001": "29岁，女性，情绪低落",
    "PS-002": "26岁，男性，心悸",
    "GP-003": "32岁，女性，胸痛",
}


def _short_complaint(complaint: str) -> str:
    """从主诉中取出一个简短的核心症状短语（去时间、去过度描述）。"""
    text = (complaint or "").strip()
    # 去末尾时间/持续时长（如「3天」「2月余」「6小时」）
    text = re.sub(r"[，,、\s]*[约近]?\d+\s*(?:天|小时|周|月|年)[余左右]*[。]*$", "", text).strip()
    # 取第一个核心症状短语（到第一个「、」「伴」「，」或句末为止）
    text = re.split(r"[、伴，。]", text, maxsplit=1)[0].strip().rstrip("，,。")
    return text


def derive_patient_brief(patient_scenario: str, case_no: str | None = None) -> str:
    """派生考生的开场信息：`年龄 + 性别 + 核心症状`。

    - ``case_no`` 命中 ``CARD_BRIEFS`` 时直接返回精心裁剪的开场信息（推荐）。
    - 否则从 ``patient_scenario`` 派生（去时间、去过度描述），作为兜底。
    不包含任何病史细节 / 诊断 / 查体 / 检查结果。派生失败时返回空串。
    """
    if case_no and case_no in CARD_BRIEFS:
        return CARD_BRIEFS[case_no]

    scenario = (patient_scenario or "").strip()
    if not scenario:
        return ""

    info = parse_patient_scenario(scenario)
    if info["complaint"]:
        head: list[str] = []
        if info["age"]:
            head.append(f"{info['age']}岁")
        label = _gender_label(info["gender"])
        if label:
            head.append(label)
        head_str = "，".join(head)
        symptom = _short_complaint(info["complaint"])
        return f"{head_str}，{symptom}" if head_str else symptom

    # 自由文本（无 一般情况/主诉 小节，如 GP-003 已由 CARD_BRIEFS 覆盖）：取年龄+性别+主诉短语
    age_m = re.search(r"(\d{1,3})\s*岁", scenario)
    gender_m = re.search(r"([男女])", scenario)
    head = []
    if age_m:
        head.append(f"{age_m.group(1)}岁")
    label = _gender_label(gender_m.group(1) if gender_m else "")
    if label:
        head.append(label)
    head_str = "，".join(head)

    symptom = ""
    if age_m:
        rest = scenario[age_m.end():].lstrip("，,。 ")
        symptom = re.split(r"[，。]", rest, maxsplit=1)[0].strip()
    else:
        symptom = re.split(r"[，。]", scenario)[0].strip()

    return f"{head_str}，{symptom}" if head_str else symptom
